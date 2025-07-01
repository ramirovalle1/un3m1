# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
import random
import xlwt
from django.template.context import Context
from django.template.loader import get_template
# from tensorflow.python.layers.utils import convert_data_format
from xlwt import *
import xlsxwriter
import io

from sga.forms import AprobarVideoMagistralForm,ArchivosCraiRecursosForm,VideoMagistralSilaboSemanalAdminForm,\
    CompendioSilaboSemanalForm,CraiRecursoSilaboSemanalForm
from sga.templatetags.sga_extras import encrypt
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre_video,generar_nombre
from sga.models import ESTADO_APROBACION_VIRTUAL, AutorprogramaAnalitico, TemaUnidadResultadoProgramaAnalitico, \
    VideoTemaProgramaAnalitico, SubtemaUnidadResultadoProgramaAnalitico, VideoSubTemaProgramaAnalitico, ProfesorMateria, \
    VideoTemaTutor, Materia, RecursoTemaProgramaAnalitico, RecursoSubTemaProgramaAnalitico, \
    UnidadResultadoProgramaAnalitico, \
    RecursoUnidadProgramaAnalitico, VideoUnidadResultadoProgramaAnalitico, Coordinacion, Carrera, Modalidad, \
    CUENTAS_CORREOS, Persona, NivelMalla, ESTADO_VIDEO_ELIMINADO, VideoUnidadResultadoProgramaAnaliticoEliminado, \
    VideoTemaProgramaAnaliticoEliminado, VideoSubTemaProgramaAnaliticoEliminado, \
    RecursoUnidadProgramaAnaliticoEliminado, RecursoTemaProgramaAnaliticoEliminado, \
    RecursoSubTemaProgramaAnaliticoEliminado, VideoMagistralSilaboSemanal, Silabo, Asignatura, DiapositivaSilaboSemanal, \
    CompendioSilaboSemanal, HistorialaprobacionVideoMagistral, CoordinadorCarrera, miinstitucion, Estado, \
    ForoSilaboSemanal, \
    TestSilaboSemanal, MaterialAdicionalSilaboSemanal, GuiaEstudianteSilaboSemanal, HistorialaprobacionCompendio, \
    HistorialaprobacionGuiaEstudiante, Profesor, SilaboSemanal, Periodo
from inno.models import ConfiguracionRecurso
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN
from sga.tasks import send_html_mail, conectar_cuenta
from typing import Any, Hashable, Iterable, Optional

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

@transaction.atomic()
def view(request):
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    global ex
    data = {}
    adduserdata(request, data)
    data['persona']= persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addvideotema':
                try:
                    newfile = None
                    if ('videot' in request.FILES or 'urlvideot' in request.POST )  and 'idvt' in request.POST and 'idup' in request.POST and 'ordent' in request.POST:
                        if 'videot' in request.FILES:
                            newfile = request.FILES['videot']
                            newfile._name = generar_nombre_video("Video_", newfile._name)
                        tema = TemaUnidadResultadoProgramaAnalitico.objects.filter(status=True, id=int(request.POST['idvt']))[0]
                        if newfile:
                            video = VideoTemaProgramaAnalitico(tema=tema, descripcion=request.POST['descripciont'], video=newfile, orden=request.POST['ordent'], estado=2)
                        else:
                            video = VideoTemaProgramaAnalitico(tema=tema, descripcion=request.POST['descripciont'],video=request.POST['urlvideot'], orden=request.POST['ordent'], estado=2)
                        video.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                videor = VideoTemaProgramaAnalitico(tema=temar, descripcion=request.POST['descripciont'], video=newfile, orden=request.POST['ordent'], estado=2)
                                videor.save(request)
                        if programa.autor:
                            video.email_notificacion_video_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un video: %s de la asignatura %s" % (video, video.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addvideounidad':
                try:
                    newfile = None
                    if  ('videou' in request.FILES or 'urlvideou' in request.POST ) and 'idu' in request.POST and 'iduap' in request.POST and 'ordenu' in request.POST:
                        if 'videou' in request.FILES:
                            newfile = request.FILES['videou']
                            newfile._name = generar_nombre_video("Video_", newfile._name)
                        unidad = UnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idu']))
                        if newfile:
                            video = VideoUnidadResultadoProgramaAnalitico(unidad=unidad, descripcion=request.POST['descripcionu'], video=newfile, orden=request.POST['ordenu'], estado=2)
                        else:
                            video = VideoUnidadResultadoProgramaAnalitico(unidad=unidad,descripcion=request.POST['descripcionu'],video=request.POST['urlvideou'], orden=request.POST['ordenu'],estado=2)
                        video.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['iduap']))
                        # for pro in programa.programasanaliticos_relacionados():
                        #     temar = UnidadResultadoProgramaAnalitico.objects.filter(descripcion=unidad.descripcion, orden=unidad.orden, unidadresultadoprogramaanalitico__orden=unidad, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #     if temar:
                        #         videor = VideoTemaProgramaAnalitico(tema=temar, descripcion=request.POST['descripciont'], video=newfile, orden=request.POST['ordent'])
                        #         videor.save(request)
                        if programa.autor:
                            video.email_notificacion_video_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un video: %s de la asignatura %s" % (video, video.unidad.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editvideounidad':
                try:
                    if 'idvu' in request.POST and 'descripcion' in request.POST and 'orden' in request.POST and 'iduap' in request.POST:
                        video = VideoUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvu']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['iduap']))
                        # for pro in programa.programasanaliticos_relacionados():
                        #     temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=video.tema.descripcion, orden=video.tema.orden, unidadresultadoprogramaanalitico__orden=video.tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #     if temar:
                        #         videor = VideoTemaProgramaAnalitico.objects.get(tema=temar, descripcion=video.descripcion, orden=video.orden)
                        #         videor.descripcion = request.POST['descripcion']
                        #         videor.orden = request.POST['orden']
                        #         videor.save(request)
                        video.descripcion = request.POST['descripcion']
                        video.orden = request.POST['orden']
                        video.save(request)
                        log(u"Editó un video: %s de la asignatura %s" % (video, video.unidad.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editvideotema':
                try:
                    if 'idvi' in request.POST and 'descripcion' in request.POST and 'orden' in request.POST and 'idup' in request.POST:
                        video = VideoTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvi']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=video.tema.descripcion, orden=video.tema.orden, unidadresultadoprogramaanalitico__orden=video.tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                videor = VideoTemaProgramaAnalitico.objects.get(tema=temar, descripcion=video.descripcion, orden=video.orden)
                                videor.descripcion = request.POST['descripcion']
                                videor.orden = request.POST['orden']
                                videor.save(request)
                        video.descripcion = request.POST['descripcion']
                        video.orden = request.POST['orden']
                        video.save(request)
                        log(u"Editó un video: %s de la asignatura %s" % (video, video.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editrecursotema':
                try:
                    if 'idri' in request.POST and 'descripcionr' in request.POST and 'ordenrt' in request.POST and 'idup' in request.POST:
                        recurso =RecursoTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idri']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=recurso.tema.descripcion, orden=recurso.tema.orden, unidadresultadoprogramaanalitico__orden=recurso.tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                recursor = RecursoTemaProgramaAnalitico.objects.get(tema=temar, descripcion=recurso.descripcion, orden=recurso.orden)
                                recursor.descripcion = request.POST['descripcionr']
                                recursor.orden = request.POST['ordenrt']
                                recursor.save(request)
                        recurso.descripcion = request.POST['descripcionr']
                        recurso.orden = request.POST['ordenrt']
                        recurso.save(request)
                        log(u"Editó un video: %s de la asignatura %s" % (recurso, recurso.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editrecursounidad':
                try:
                    if 'idru' in request.POST and 'descripcionru' in request.POST and 'ordenru' in request.POST and 'idrup' in request.POST:
                        recurso =RecursoUnidadProgramaAnalitico.objects.get(status=True, id=int(request.POST['idru']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idrup']))
                        # for pro in programa.programasanaliticos_relacionados():
                        #     temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=recurso.tema.descripcion, orden=recurso.tema.orden, unidadresultadoprogramaanalitico__orden=recurso.tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #     if temar:
                        #         recursor = RecursoTemaProgramaAnalitico.objects.get(tema=temar, descripcion=recurso.descripcion, orden=recurso.orden)
                        #         recursor.descripcion = request.POST['descripcionr']
                        #         recursor.orden = request.POST['ordenrt']
                        #         recursor.save(request)
                        recurso.descripcion = request.POST['descripcionru']
                        recurso.orden = request.POST['ordenru']
                        recurso.save(request)
                        # log(u"Editó un video: %s de la asignatura %s" % (recurso, recurso.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addvideosubtema':
                try:
                    newfile = None
                    if ('video' in request.FILES or 'urlvideost' in request.POST )and 'idvs' in request.POST and 'idup' in request.POST and 'ordenst' in request.POST:
                        if 'video' in request.FILES:
                            newfile = request.FILES['video']
                            newfile._name = generar_nombre_video("Video_", newfile._name)
                        subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvs']))
                        if newfile:
                            video = VideoSubTemaProgramaAnalitico(subtema=subtema, descripcion=request.POST['descripcion'], video=newfile, orden=request.POST['ordenst'], estado=2)
                        else:
                            video = VideoSubTemaProgramaAnalitico(subtema=subtema,descripcion=request.POST['descripcion'],video=request.POST['urlvideost'], orden=request.POST['ordenst'],estado=2)
                        video.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        for pro in programa.programasanaliticos_relacionados():
                            subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=subtema.descripcion, orden=subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if subtemar:
                                videor = VideoSubTemaProgramaAnalitico(subtema=subtemar, descripcion=request.POST['descripcion'], video=newfile, orden=request.POST['ordenst'], estado=2)
                                videor.save(request)
                        if programa.autor:
                            video.email_notificacion_video_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un video: %s de la asignatura %s" % (video,  video.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editvideosubtema':
                try:
                    if not len(request.POST['descripcion']) >0:
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción es obligatoria."})
                    if not 'idvi' in request.POST:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                    if 'idvi' in request.POST and 'descripcion' in request.POST and 'orden' in request.POST and 'idup' in request.POST:
                        video = VideoSubTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvi']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        for pro in programa.programasanaliticos_relacionados():
                            subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=video.subtema.descripcion, orden=video.subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=video.subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=video.subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=video.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if subtemar:
                                videor = VideoSubTemaProgramaAnalitico.objects.get(subtema=subtemar, descripcion=video.descripcion, orden=video.orden)
                                videor.descripcion = request.POST['descripcion']
                                videor.orden = request.POST['orden']
                                videor.save(request)
                        video.descripcion = request.POST['descripcion']
                        video.orden = request.POST['orden']
                        video.save(request)
                        log(u"Adito la descripcion del video: %s de la asignatura %s" % (video, video.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addrecursounidad':
                try:
                    newfile = None
                    tiporecurso_unidad = None
                    if ('recursoru' in request.FILES or 'urlrecursou' in request.POST) and 'idru' in request.POST and 'idruap' in request.POST and 'ordenru' in request.POST:
                        if 'recursoru' in request.FILES:
                            newfile = request.FILES['recursoru']
                            newfile._name = generar_nombre("Documento_", newfile._name)
                        if 'id_tiporecurso_unidad' in request.POST:
                            tiporecurso_unidad = request.POST['id_tiporecurso_unidad']
                        unidad = UnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idru']))
                        if newfile:
                            recurso = RecursoUnidadProgramaAnalitico(unidad=unidad, descripcion=request.POST['descripcionru'], recurso=newfile, orden=request.POST['ordenru'],tiporecurso=tiporecurso_unidad, estado=2)
                        else:
                            recurso = RecursoUnidadProgramaAnalitico(unidad=unidad, descripcion=request.POST['descripcionru'], recurso=request.POST['urlrecursou'], orden=request.POST['ordenru'],tiporecurso=tiporecurso_unidad, estado=2)
                        recurso.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idruap']))
                        # for pro in programa.programasanaliticos_relacionados():
                        #     temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #     if temar:
                        #         videor = RecursoTemaProgramaAnalitico(tema=temar, descripcion=request.POST['descripciontr'], video=newfile, orden=request.POST['ordentr'])
                        #         videor.save(request)
                        if programa.autor:
                            recurso.email_notificacion_recurso_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un recurso: %s de la asignatura %s" % (recurso, recurso.unidad.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "add")
                        return JsonResponse({"result": "ok", "ban": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addrecursotema':
                try:
                    newfile = None
                    tiporecurso_tema = None
                    if ('recursotr' in request.FILES or 'urlrecursost' in request.POST) and 'idrt' in request.POST and 'idrp' in request.POST and 'ordentr' in request.POST:
                        if 'recursotr' in request.FILES:
                            newfile = request.FILES['recursotr']
                            newfile._name = generar_nombre("Documento_", newfile._name)
                        tema = TemaUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idrt']))
                        if 'id_tiporecurso_tema' in request.POST:
                            tiporecurso_tema = request.POST['id_tiporecurso_tema']
                        if newfile:
                            recurso = RecursoTemaProgramaAnalitico(tema=tema, descripcion=request.POST['descripciontr'], recurso=newfile, orden=request.POST['ordentr'], tiporecurso=tiporecurso_tema, estado=2)
                        else:
                            recurso = RecursoTemaProgramaAnalitico(tema=tema, descripcion=request.POST['descripciontr'], recurso=request.POST['urlrecursost'], orden=request.POST['ordentr'], tiporecurso=tiporecurso_tema, estado=2)
                        recurso.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idrp']))
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                videor = RecursoTemaProgramaAnalitico(tema=temar, descripcion=request.POST['descripciontr'], video=newfile, orden=request.POST['ordentr'],tiporecurso=tiporecurso_tema, estado=2)
                                videor.save(request)
                        if programa.autor:
                            recurso.email_notificacion_recurso_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un recurso: %s de la asignatura %s" % (recurso, recurso.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "add")
                        return JsonResponse({"result": "ok", "ban": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detallevidelo_tema':
                try:
                    if 'id' in request.POST and 'idup' in request.POST:
                        tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        data['videos'] = tema.videotemaprogramaanalitico_set.filter(status=True).order_by('orden')
                        data['recursos'] = tema.recursotemaprogramaanalitico_set.filter(status=True).order_by('orden')
                        data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        template = get_template("adm_gestionvideos/detallevideo_tema.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'Tema: %s'%tema.descripcion })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detallevideo_unidad':
                try:
                    if 'id' in request.POST and 'iduap' in request.POST:
                        unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        data['videos'] = unidad.videounidadresultadoprogramaanalitico_set.filter(status=True).order_by('orden')
                        data['recursos'] = unidad.recursounidadprogramaanalitico_set.filter(status=True).order_by('orden')
                        data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.POST['iduap']))
                        template = get_template("adm_gestionvideos/detalle_video_unidad.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'Tema: %s'%unidad.descripcion })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'play_video_unidad':
                try:
                    if 'id' in request.POST:
                        data['videounidad'] = video = VideoUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_gestionvideos/play_video_unidad.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'%s'%video.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'play_video_tema':
                try:
                    if 'id' in request.POST:
                        data['videotema'] = video = VideoTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_gestionvideos/play_video_tema.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'%s'%video.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detallevidelo_subtema':
                try:
                    if 'id' in request.POST and 'idup' in request.POST:
                        subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        data['videos'] = subtema.videosubtemaprogramaanalitico_set.filter(status=True).order_by('orden')
                        data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        data['recursos'] = subtema.recursosubtemaprogramaanalitico_set.filter(status=True).order_by('orden')
                        template = get_template("adm_gestionvideos/detallevideo_subtema.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'Tema: %s'%subtema.descripcion })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'play_video_subtema':
                try:
                    if 'id' in request.POST:
                        data['video'] = video = VideoSubTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_gestionvideos/play_video_subtema.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'%s'%video.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delvideounidad':
                try:
                    if 'id' in request.POST:
                        unidad = VideoUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del tema: %s' % (unidad,unidad.descripcion) , request, "del")
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['iduap']))
                        tema = unidad.unidad
                        video_eliminado = VideoUnidadResultadoProgramaAnaliticoEliminado(unidad=unidad.unidad,
                                                                                         descripcion=unidad.descripcion,
                                                                                         video=unidad.video,
                                                                                         persona=Persona.objects.get(
                                                                                             usuario=request.user),
                                                                                         observacion=str(request.POST[
                                                                                                             'observacion']),
                                                                                         fechacambioestado=datetime.now())
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                videor = VideoTemaProgramaAnalitico.objects.filter(tema=temar)
                                videor.delete()
                        pr1=video_eliminado.save()
                        print(pr1)
                        pr1=unidad.delete()
                        print(pr1)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print(str(ex))
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. " + str(ex)})

            elif action == 'delvideotema':
                try:
                    if 'id' in request.POST:
                        video = VideoTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del tema: %s' % (video,video.tema) , request, "del")
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        tema = video.tema
                        video_eliminado = VideoTemaProgramaAnaliticoEliminado(tema=tema,descripcion=video.descripcion,
                                                                              persona=Persona.objects.get(usuario=request.user),
                                                                              video=video.video,
                                                                              observacion=str(request.POST['observacion']),
                                                                              fechacambioestado=datetime.now())
                        for pro in programa.programasanaliticos_relacionados():
                            temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if temar:
                                videor = VideoTemaProgramaAnalitico.objects.filter(tema=temar)
                                videor.delete()
                        video_eliminado.save()
                        video.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delrecursounidad':
                try:
                    if 'id' in request.POST:
                        unidad = RecursoUnidadProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del tema: %s' % (unidad,unidad.descripcion) , request, "del")
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idaup']))
                        # tema = recurso.tema
                        # for pro in programa.programasanaliticos_relacionados():
                        #     temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #     if temar:
                        #         recursor = RecursoTemaProgramaAnalitico.objects.filter(tema=temar)
                        #         recursor.delete()
                        recurso_eliminado=RecursoUnidadProgramaAnaliticoEliminado(unidad=unidad.unidad, descripcion=unidad.descripcion, recurso=unidad.recurso,
                                                                                  persona=Persona.objects.get(usuario=request.user),
                                                                                  tiporecurso=unidad.tiporecurso,
                                                                                  observacion= str(request.POST['observacion']),
                                                                                  fechacambioestado=datetime.now())
                        recurso_eliminado.save()
                        unidad.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delrecursotema':
                try:
                    if 'id' in request.POST:
                        recurso = RecursoTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del tema: %s' % (recurso,recurso.tema) , request, "del")
                        #programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        #tema = recurso.tema
                        #for pro in programa.programasanaliticos_relacionados():
                        #    temar = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=tema.descripcion, orden=tema.orden, unidadresultadoprogramaanalitico__orden=tema.unidadresultadoprogramaanalitico.orden, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #    if temar:
                        #        recursor = RecursoTemaProgramaAnalitico.objects.filter(tema=temar)
                        #        recursor.delete()
                        recurso_eliminado = RecursoTemaProgramaAnaliticoEliminado(tema=recurso.tema,
                                                                                  descripcion=recurso.descripcion,
                                                                                  recurso=recurso.recurso,
                                                                                  persona=Persona.objects.get(
                                                                                      usuario=request.user),
                                                                                  tiporecurso=recurso.tiporecurso,
                                                                                  observacion=str(
                                                                                      request.POST['observacion']),
                                                                                  fechacambioestado=datetime.now())
                        recurso_eliminado.save()
                        recurso.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delvideosubtema':
                try:
                    if 'id' in request.POST:
                        video = VideoSubTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del subtema: %s' % (video,video.subtema) , request, "del")
                        #programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idup']))
                        #subtema = video.subtema
                        #for pro in programa.programasanaliticos_relacionados():
                        #    subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=subtema.descripcion, orden=subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #    if subtemar:
                        #        videor = VideoSubTemaProgramaAnalitico.objects.filter(subtema=subtemar)
                        #        videor.delete()
                        video_eliminado = VideoSubTemaProgramaAnaliticoEliminado(subtema=video.subtema, descripcion=video.descripcion, video=video.video,
                                                                                 persona=Persona.objects.get(usuario=request.user),
                                                                                 observacion=str(request.POST['observacion']),
                                                                                 fechacambioestado=datetime.now())
                        video_eliminado.save()
                        video.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addvideotutor':
                try:
                    if 'video' in request.FILES and 'idt' in request.POST and 'orden' in request.POST and 'idm' in request.POST:
                        newfile = request.FILES['video']
                        newfile._name = generar_nombre_video("", newfile._name)
                        tema = TemaUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idt']))
                        materia = Materia.objects.get(status=True, id=int(request.POST['idm']))
                        video = VideoTemaTutor(tema=tema, descripcion=request.POST['descripcion'], video=newfile, orden=request.POST['orden'], materia=materia)
                        video.save(request)
                        # video.email_notificacion_video_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un video: %s de la asignatura %s" % (video, video.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": False})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editvideotutor':
                try:
                    if 'idvi' in request.POST and 'descripcion' in request.POST and 'orden' in request.POST and 'idm' in request.POST:
                        newfile = None
                        materia = Materia.objects.get(id=int(request.POST['idm']))
                        if 'video' in request.FILES:
                            newfile = request.FILES['video']
                            newfile._name = generar_nombre_video("", newfile._name)
                        video = VideoTemaTutor.objects.get(status=True, id=int(request.POST['idvi']))
                        video.descripcion = request.POST['descripcion']
                        video.orden = request.POST['orden']
                        video.materia=materia
                        if newfile:
                            video.video = newfile
                        video.save(request)
                        log(u"Editó un video: %s de la asignatura %s" % (video, video.tema.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detallevideo_tutor':
                try:
                    if 'id' in request.POST and 'idm' in request.POST:
                        data['materia'] = Materia.objects.get(id=int(request.POST['idm']))
                        tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        data['videos'] = tema.videotematutor_set.filter(status=True).order_by('orden')
                        template = get_template("adm_gestionvideos/detallevideo_tutor.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'Tema: %s'%tema.descripcion })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'play_video_tutor':
                try:
                    if 'id' in request.POST:
                        data['video'] = video = VideoTemaTutor.objects.get(pk=int(request.POST['id']))
                        template = get_template("adm_gestionvideos/play_video_tutor.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content, 'title':u'%s' % video.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delvideotutor':
                try:
                    if 'id' in request.POST:
                        video = VideoTemaTutor.objects.get(pk=int(request.POST['id']))
                        log(u'Elimino el video %s del tema: %s' % (video, video.tema), request, "del")
                        video.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobar_unidades':
                try:
                    data['unidad'] = unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                    unidad.estado=2
                    unidad.save()

                    for temas in unidad.temaunidadresultadoprogramaanalitico_set.all():
                        temas.estado=2
                        temas.save()
                        for subtemas in temas.subtemaunidadresultadoprogramaanalitico_set.all():
                            subtemas.estado=2
                            subtemas.save()

                    log(u'Aprobación de temas: %s' % unidad, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobar_videotema':
                try:
                    data['tema'] = tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                    tema.estado=2
                    tema.save()
                    # videos = tema.videotemaprogramaanalitico_set.filter(status=True)
                    # # videos = tema.videotemaprogramaanalitico_set.filter(status=True)
                    # for video in videos:
                    #     video.estado=2
                    #     video.save()

                    subtemas = tema.subtemaunidadresultadoprogramaanalitico_set.all()
                    for vsubtema in subtemas:
                        vsubtema.estado=2
                        vsubtema.save()
                        # if vsubtema.videosubtemaprogramaanalitico_set.exists():
                        # for videos in vsubtema.videosubtemaprogramaanalitico_set.filter(status=True):
                        #     videos.estado=2
                        #     videos.save()

                    log(u'Aprobación de videos: %s' % tema, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'habilitar_videotema':
                try:
                    data['tema'] = tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                    tema.estado=1
                    tema.save()
                    # videos = tema.videotemaprogramaanalitico_set.filter(status=True)
                    # for video in videos:
                    #     video.estado=1
                    #     video.save()
                    subtemas = tema.subtemaunidadresultadoprogramaanalitico_set.all()
                    for vsubtema in subtemas:
                        vsubtema.estado = 1
                        vsubtema.save()
                        # if vsubtema.videosubtemaprogramaanalitico_set.exists():
                        #     for videos in vsubtema.videosubtemaprogramaanalitico_set.filter(status=True):
                        #         videos.estado = 1
                        #         videos.save()
                    log(u'Habilitar videos: %s' % tema, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'habilitar_unidades':
                try:
                    data['unidad'] = unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                    unidad.estado = 1
                    unidad.save()

                    for temas in unidad.temaunidadresultadoprogramaanalitico_set.all():
                        temas.estado = 1
                        temas.save()
                        for subtemas in temas.subtemaunidadresultadoprogramaanalitico_set.all():
                            subtemas.estado = 1
                            subtemas.save()
                    log(u'Habilitar Unidades: %s' % unidad, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addrecursosubtema':
                try:
                    newfile = None
                    tiporecurso_subtema = None
                    if 'recurso' in request.FILES and 'idrs' in request.POST and 'idrup' in request.POST and 'ordenrst' in request.POST:
                        newfile = request.FILES['recurso']
                        newfile._name = generar_nombre("Documento_", newfile._name)
                        if 'id_tiporecurso_subtema' in request.POST:
                            tiporecurso_subtema = request.POST['id_tiporecurso_subtema']
                        subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idrs']))
                        recurso = RecursoSubTemaProgramaAnalitico(subtema=subtema, descripcion=request.POST['descripcionrst'], recurso=newfile, orden=request.POST['ordenrst'], tiporecurso=tiporecurso_subtema, estado=2)
                        recurso.save(request)
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idrup']))
                        for pro in programa.programasanaliticos_relacionados():
                            subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=subtema.descripcion, orden=subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if subtemar:
                                recursor = VideoSubTemaProgramaAnalitico(subtema=subtemar, descripcion=request.POST['descripcion'], video=newfile, orden=request.POST['ordenst'], tiporecurso=tiporecurso_subtema, estado=2)
                                recursor.save(request)
                        if programa.autor:
                            recurso.email_notificacion_recurso_subido(request.session['nombresistema'], programa.autor.persona.nombre_completo_inverso())
                        log(u"Adicionó un recurso: %s de la asignatura %s" % (recurso,  recurso.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editrecursosubtemas':
                try:
                    if not len(request.POST['descripcionrs']) >0:
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción es obligatoria."})
                    if not 'idris' in request.POST:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                    if 'idris' in request.POST and 'descripcionrs' in request.POST and 'ordenrs' in request.POST and 'idrup' in request.POST:
                        recurso = RecursoSubTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idris']))
                        programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idrup']))
                        for pro in programa.programasanaliticos_relacionados():
                            subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=recurso.subtema.descripcion, orden=recurso.subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=recurso.subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=recurso.subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=recurso.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                            if subtemar:
                                recursor = VideoSubTemaProgramaAnalitico.objects.get(subtema=subtemar, descripcion=recurso.descripcion, orden=recurso.orden)
                                recursor.descripcion = request.POST['descripcionrs']
                                recursor.orden = request.POST['ordenrs']
                                recursor.save(request)
                        recurso.descripcion = request.POST['descripcionrs']
                        recurso.orden = request.POST['ordenrs']
                        recurso.save(request)
                        log(u"Adito la descripcion del video: %s de la asignatura %s" % (recurso, recurso.subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.contenidoresultadoprogramaanalitico.programaanaliticoasignatura.asignaturamalla.asignatura.nombre), request, "edit")
                        return JsonResponse({"result": "ok", "ban": True})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delrecursosubtema':
                try:
                    if 'id' in request.POST:
                        recurso = RecursoSubTemaProgramaAnalitico.objects.get(pk=int(request.POST['id']))
                        #log(u'Elimino el recurso %s del subtema: %s' % (recurso,recurso.subtema) , request, "del")
                        #programa = AutorprogramaAnalitico.objects.get(pk=int(request.POST['idrup']))
                        #subtema = recurso.subtema
                        #for pro in programa.programasanaliticos_relacionados():
                        #    subtemar = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion=subtema.descripcion, orden=subtema.orden, temaunidadresultadoprogramaanalitico__descripcion=subtema.temaunidadresultadoprogramaanalitico.descripcion, temaunidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=subtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura=pro)[0]
                        #    if subtemar:
                        #        recursor = VideoSubTemaProgramaAnalitico.objects.filter(subtema=subtemar)
                        #        recursor.delete()
                        recurso_eliminado = RecursoSubTemaProgramaAnaliticoEliminado(subtema=recurso.subtema,
                                                                                     descripcion=recurso.descripcion,
                                                                                     recurso=recurso.recurso,
                                                                                     persona=Persona.objects.get(
                                                                                         usuario=request.user),
                                                                                     tiporecurso=recurso.tiporecurso,
                                                                                     observacion=str(
                                                                                         request.POST['observacion']),
                                                                                     fechacambioestado=datetime.now())
                        recurso_eliminado.save()
                        recurso.delete()
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarvideounidad':
                try:
                    if 'idvi' in request.POST and 'iduap' in request.POST and 'estadovideo' in request.POST and 'obsvu' in request.POST:
                        estado =  int(request.POST['estadovideo'])
                        videounidad = VideoUnidadResultadoProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvi']))
                        videounidad.observacion = request.POST['obsvu']
                        videounidad.estado = estado
                        videounidad.aprueba = persona
                        videounidad.fechacambioestado = datetime.now()
                        videounidad.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':1,
                                            'persona': persona,'videounidad':videounidad,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de video unidad autor %s %s" % (videounidad.id, videounidad), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarvideotema':
                try:
                    if 'idvi' in request.POST and 'iduap' in request.POST and 'estadovideo' in request.POST and 'obsvu' in request.POST:
                        estado=int(request.POST['estadovideo'])
                        videotema = VideoTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvi']))
                        videotema.observacion = request.POST['obsvu']
                        videotema.estado = estado
                        videotema.aprueba = persona
                        videotema.fechacambioestado = datetime.now()
                        videotema.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':2,
                                            'persona': persona,'videotema':videotema,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de video tema autor %s %s" % (videotema.id, videotema), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarvideosubtema':
                try:
                    if 'idvi' in request.POST and 'iduap' in request.POST and 'estadovideo' in request.POST and 'obsvu' in request.POST:
                        estado = int(request.POST['estadovideo'])
                        videosubtema = VideoSubTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idvi']))
                        videosubtema.observacion = request.POST['obsvu']
                        videosubtema.estado = estado
                        videosubtema.aprueba = persona
                        videosubtema.fechacambioestado = datetime.now()
                        videosubtema.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':3,
                                            'persona': persona,'videosubtema':videosubtema,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de video sub tema autor %s %s" % (videosubtema.id, videosubtema), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarrecursounidad':
                try:
                    if 'idre' in request.POST and 'iduap' in request.POST and 'estadorecurso' in request.POST and 'observacionrecurso' in request.POST:
                        estado=int(request.POST['estadorecurso'])
                        recurso = RecursoUnidadProgramaAnalitico.objects.get(status=True, id=int(request.POST['idre']))
                        recurso.observacion = request.POST['observacionrecurso']
                        recurso.estado = estado
                        recurso.aprueba = persona
                        recurso.fechacambioestado = datetime.now()
                        recurso.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':4,
                                            'persona': persona,'recurso':recurso,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de recurso sub tema autor %s %s" % (recurso.id, recurso), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarrecursotema':
                try:
                    if 'idre' in request.POST and 'iduap' in request.POST and 'estadorecurso' in request.POST and 'observacionrecurso' in request.POST:
                        estado = int(request.POST['estadorecurso'])
                        recurso = RecursoTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idre']))
                        recurso.observacion = request.POST['observacionrecurso']
                        recurso.estado = estado
                        recurso.aprueba = persona
                        recurso.fechacambioestado = datetime.now()
                        recurso.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':5,
                                            'persona': persona,'recursotema':recurso,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de recurso  tema autor %s %s" % (recurso.id, recurso), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobarrecursosubtema':
                try:
                    if 'idre' in request.POST and 'iduap' in request.POST and 'estadorecurso' in request.POST and 'observacionrecurso' in request.POST:
                        estado = int(request.POST['estadorecurso'])
                        recurso = RecursoSubTemaProgramaAnalitico.objects.get(status=True, id=int(request.POST['idre']))
                        recurso.observacion = request.POST['observacionrecurso']
                        recurso.estado = estado
                        recurso.aprueba = persona
                        recurso.fechacambioestado=datetime.now()
                        recurso.save(request)
                        if estado == 3:
                            lista = []
                            lista.append('sop_docencia_crai@unemi.edu.ec')
                            send_html_mail("Video rechazado", "emails/videorechazadoaautor.html",
                                           {'sistema': u'Campus Virtual',
                                            'fecha': datetime.now().date,'opc':6,
                                            'persona': persona,'recursosubtema':recurso,
                                            'dominio': EMAIL_DOMAIN}, lista, [],
                                           cuenta=CUENTAS_CORREOS[20][1])
                        log(u"Cambia estado de recurso sub tema autor %s %s" % (recurso.id, recurso), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'detallevidmagistral':
                try:
                    data['videomagistral'] = videomagistral = VideoMagistralSilaboSemanal.objects.get(pk=int(request.POST['coodigovideo']))
                    # diapositiva = None
                    compendio = None
                    # if  DiapositivaSilaboSemanal.objects.filter(silabosemanal=videomagistral.silabosemanal).exists():
                    #     diapositiva = DiapositivaSilaboSemanal.objects.get(silabosemanal=videomagistral.silabosemanal)
                    if CompendioSilaboSemanal.objects.filter(silabosemanal=videomagistral.silabosemanal).exists():
                        compendio = CompendioSilaboSemanal.objects.filter(silabosemanal=videomagistral.silabosemanal).order_by('-pk').first()
                    # data['diapositiva'] = diapositiva
                    data['compendio'] = compendio
                    data['historialaprobacion'] = videomagistral.historialaprobacionvideomagistral_set.filter(status=True).order_by('id')
                    template = get_template("adm_gestionvideos/detallevidmagistral.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargavidmagistral':
                try:
                    f = AprobarVideoMagistralForm(request.POST, request.FILES)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 429916160:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 500 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el avideo magistral esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.mp4':
                                    newfile._name = generar_nombre("vidmagistral_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, video magistral solo en formato .mp4"})
                    if f.is_valid():
                        vidmagistral = VideoMagistralSilaboSemanal.objects.get(pk=int(encrypt(request.POST['id'])))
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("vidmagistral", newfile._name)
                                vidmagistral.archivovideomagistral = newfile
                        vidmagistral.urlcrai = f.cleaned_data['url']
                        if vidmagistral.estado_id == 4:
                            vidmagistral.save(request)
                            from Moodle_Funciones import CrearVidMagistralMoodle
                            value, msg = CrearVidMagistralMoodle(vidmagistral.id, persona)
                            if not value:
                                raise NameError(msg)
                            historial = HistorialaprobacionVideoMagistral(material=vidmagistral,
                                                                          observacion="CARGARDO POR CRAI",
                                                                          estado_id=4)
                            historial.save(request)
                        else:
                            vidmagistral.estado_id = 2
                            vidmagistral.save(request)
                            historial = HistorialaprobacionVideoMagistral(material=vidmagistral,
                                                                          observacion=f.cleaned_data['observacion'],
                                                                          estado_id=2)
                            historial.save(request)
                        personadocente = Persona.objects.get(usuario=vidmagistral.silabosemanal.silabo.profesor.persona.usuario, status=True)
                        correo = personadocente.lista_emails_envio()
                        if CoordinadorCarrera.objects.filter(status=True, carrera=vidmagistral.silabosemanal.silabo.materia.asignaturamalla.malla.carrera, periodo=periodo, sede=1, tipo=3):
                            coordinadordecarrera = CoordinadorCarrera.objects.filter(status=True, carrera=vidmagistral.silabosemanal.silabo.materia.asignaturamalla.malla.carrera, periodo=periodo, sede=1, tipo=3)[0]
                            correo = correo + coordinadordecarrera.persona.lista_emails_envio()
                        nombrerecurso = 'VIDEO MAGISTRAL'
                        nombre_carrera = vidmagistral.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre_completo()
                        correo.append('sop_docencia_crai@unemi.edu.ec')
                        semana = vidmagistral.silabosemanal.numsemana
                        cuenta=CUENTAS_CORREOS[0][1]
                        send_html_mail("SGA - VIDEOS MAGISTRALES - %s"%nombre_carrera, "emails/videomagistral_revision.html",
                                       {'sistema': request.session['nombresistema'], 'nombredocente': personadocente, 'nombrecarrera': nombre_carrera,
                                        'nombrerecurso': nombrerecurso, 'semana': semana, 'vidmagistral': vidmagistral,
                                        't': miinstitucion()}, correo, [], cuenta=cuenta)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Error, ar guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al subir archivo. %s'%ex})

            elif action == 'detalletarea':
                try:
                    tipo = int(request.POST['codtipo'])

                    if tipo == 4:
                        data['guiaestudiante'] = guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = guiaestudiante.historialaprobacionguiaestudiante_set.filter(status=True).order_by('id')
                        data['formatos'] = guiaestudiante.mis_formatos(periodo)
                        # if guiaestudiante.estado.id in [2, 3,5]:
                        data['form'] = ArchivosCraiRecursosForm
                        template = get_template("adm_gestionvideos/detalleguiaestudiante.html")
                    if tipo == 7:
                        data['title'] = u'Evidencia Practicas'
                        data['compendio'] = compendio = CompendioSilaboSemanal.objects.get(
                            pk=int(request.POST['idtar']))
                        data['historialaprobacion'] = compendio.historialaprobacioncompendio_set.filter(
                            status=True).order_by('id')
                        data['formatos'] = compendio.mis_formatos(periodo)
                        # if compendio.estado.id in [2, 3,5]:
                        data['form'] = ArchivosCraiRecursosForm
                        template = get_template("adm_gestionvideos/detallecompendio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'buscar_materias':
                try:
                    lista = []
                    if int(request.POST['idcarr'])>0:
                        carrera = Carrera.objects.get(pk=request.POST['idcarr'])
                        for materia in Materia.objects.filter(status=True,asignaturamalla__malla__carrera=carrera, nivel__periodo=periodo):
                            lista.append([materia.id, u"%s"%materia])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscar_profesor':
                try:
                    lista = []
                    if int(request.POST['idmat']) >0:
                        materia = Materia.objects.get(pk=request.POST['idmat'])
                        for profmat in ProfesorMateria.objects.filter(status=True,materia=materia,activo=True).distinct('profesor'):
                            lista.append([profmat.profesor.id, u"%s"%profmat.profesor])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addcompendio':
                try:
                    f = ArchivosCraiRecursosForm(request.POST, request.FILES)
                    if not f.is_valid():
                        raise NameError(u"Existen problemas en el formulario.")
                    compendio = CompendioSilaboSemanal.objects.get(pk=request.POST['id'])
                    if 'archivo_logo' in request.FILES:
                        archivo_logo = request.FILES['archivo_logo']
                        if archivo_logo.size > 50485760:
                            raise NameError(u"Error, archivo mayor a 50 Mb.")
                            # return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        else:
                            newfilesrubd = archivo_logo._name
                            ext = newfilesrubd[newfilesrubd.rfind("."):]
                            if ext == ".pdf" or ext == ".PDF":
                                archivo_logo._name = generar_nombre("archivologocompendio_", archivo_logo._name)
                                compendio.archivo_logo = archivo_logo
                            else:
                                raise NameError(u"Error, archivo del compendio con logo solo en pdf")
                                # return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                    else:
                        raise NameError(u"Error, archivo del compendio con logo es obligatorio.")

                    if 'archivo_sin_logo' in request.FILES:
                        archivo_sin_logo = request.FILES['archivo_sin_logo']
                        if archivo_sin_logo.size > 50485760:
                            raise NameError(u"Error, archivo mayor a 50 Mb.")
                            # return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        else:
                            newfilesrubd1 = archivo_sin_logo._name
                            ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                            if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                archivo_sin_logo._name = generar_nombre("archivosinlogocompendio_", archivo_sin_logo._name)
                                compendio.archivo_sin_logo = archivo_sin_logo
                            else:
                                raise NameError(u"Error, archivo del compendio sin logo solo en .doc o .docx")
                                # return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})
                    if compendio.estado_id ==4:
                        compendio.save(request)
                        from Moodle_Funciones import CrearCompendioMoodle
                        value, msg = CrearCompendioMoodle(compendio.id, persona)
                        if not value:
                            raise NameError(msg)
                        historial = HistorialaprobacionCompendio(compendio=compendio,
                                                                 estado_id=4,
                                                                 observacion="CARGADO POR CRAI")
                        historial.save(request)
                    else:
                        compendio.estado_id = 2
                        compendio.save(request)
                        historial = HistorialaprobacionCompendio(compendio=compendio,
                                                                 estado_id=2,
                                                                 observacion="CARGADO POR CRAI")
                        historial.save(request)
                    log(u'Cambia de estado compendio crai : %s ' % (compendio), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})

            elif action == 'addguiaestudiante':
                try:
                    f = ArchivosCraiRecursosForm(request.POST, request.FILES)
                    if f.is_valid():
                        guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=request.POST['id'])
                        if 'archivo_logo' in request.FILES:
                            archivo_logo = request.FILES['archivo_logo']
                            if archivo_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd = archivo_logo._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".pdf" or ext == ".PDF":
                                    archivo_logo._name = generar_nombre("archivologoguiaestudiante_", archivo_logo._name)
                                    guiaestudiante.archivo_logo = archivo_logo
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, archivo del compendio con logo es obligatorio."})

                        if 'archivo_sin_logo' in request.FILES:
                            archivo_sin_logo = request.FILES['archivo_sin_logo']
                            if archivo_sin_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd1 = archivo_sin_logo._name
                                ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                    archivo_sin_logo._name = generar_nombre("archivosinlogoguiaestudiante_", archivo_sin_logo._name)
                                    guiaestudiante.archivo_sin_logo = archivo_sin_logo
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})
                        # else:
                        #     return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio sin logo es obligatorio."})
                        if guiaestudiante.estado_id == 4:
                            guiaestudiante.save(request)
                            from Moodle_Funciones import CrearGuiaestudianteMoodle
                            value, msg = CrearGuiaestudianteMoodle(guiaestudiante.id, persona)
                            if not value:
                                raise NameError(msg)
                            historial = HistorialaprobacionGuiaEstudiante(
                                guiaestudiante=guiaestudiante,
                                estado_id=4,
                                observacion="CARGADO POR CRAI")
                            historial.save(request)
                        else:
                            guiaestudiante.estado_id = 2
                            guiaestudiante.save(request)
                            historial = HistorialaprobacionGuiaEstudiante(
                                guiaestudiante=guiaestudiante,
                                estado_id=2,
                                observacion="CARGADO POR CRAI")
                            historial.save(request)
                        log(u'Cambia de estado guia estudiante crai : %s ' % (guiaestudiante),  request,  "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})

            elif action == 'addsolicitudvideomagistral':
                try:
                    f = VideoMagistralSilaboSemanalAdminForm(request.POST, request.FILES)
                    newfile = None
                    presentacion_video = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 429916160:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 500 Mb."})
                            elif newfile.size <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, el avideo magistral esta vacío."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.mp4':
                                    newfile._name = generar_nombre("vidmagistral_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, video magistral solo en formato .mp4"})


                    if not request.POST['url'] and not 'archivo' in request.FILES:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe ingresar presentación de video o una url."})
                    silabosemanal=SilaboSemanal.objects.get(id=int(request.POST['semana']))
                    if not VideoMagistralSilaboSemanal.objects.filter(status=True,silabosemanal=silabosemanal).exists():
                        vidmagistral = VideoMagistralSilaboSemanal(archivovideomagistral=newfile,
                                                                   urlcrai = request.POST['url'],
                                                                   estado_id = 2,tipomaterial=2,
                                                                   tiporecurso=1,presentacion_validado=True,
                                                                   tipograbacion=2,silabosemanal=silabosemanal,
                                                                   nombre='VIDEOMAGISTRAL_S' + str(silabosemanal.numsemana),
                                                                   descripcion=request.POST['observacion'])
                        vidmagistral.save(request)
                        historial = HistorialaprobacionVideoMagistral(material=vidmagistral,
                                                                      observacion=request.POST['observacion'],
                                                                      estado_id=2)
                        historial.save(request)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ya tiene un video en la materia y semana seleccionada.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

            elif action == 'eliminar_video_silabo':
                try:
                    if 'id' in request.POST:
                        video = VideoMagistralSilaboSemanal.objects.get(pk=int(encrypt(request.POST['id'])))
                        log(u'Elimino el video %s de: %s' % (video, video.silabosemanal), request, "del")
                        video.status=False
                        video.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addcompendiovirtual':
                try:
                    silabosemanal = SilaboSemanal.objects.get(id=int(encrypt(request.POST['id'])))
                    lista_formato = []
                    lista_extension = []
                    if ConfiguracionRecurso.objects.filter(status=True, tiporecurso=2,
                                                           carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                           periodo=periodo).exists():
                        configuracion = ConfiguracionRecurso.objects.filter(status=True, tiporecurso=2,
                                                                            carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                            periodo=periodo)[0]
                        for format in configuracion.formato.all():
                            lista_formato.append(format.nombre)
                            for extension in format.extension.all():
                                lista_extension.append(extension.nombre)
                    f = CraiRecursoSilaboSemanalForm(request.POST, request.FILES)
                    newfilecompendio=None
                    archivo_logo=None
                    archivo_sin_logo=None
                    if f.is_valid():
                        if 'archivooriginal' in request.FILES:
                            newfilecompendio = request.FILES['archivooriginal']
                            if newfilecompendio.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilescompendiod = newfilecompendio._name
                                ext = newfilescompendiod[newfilescompendiod.rfind("."):]
                                ext = ext.lower()
                                if lista_extension:
                                    if ext in lista_extension:
                                        newfilecompendio._name = generar_nombre("archivocompendio_", newfilecompendio._name)
                                    else:
                                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de compendio solo en %s" % (
                                                                 lista_extension)})
                                elif ext == ".pdf" or ext == ".PDF":
                                    newfilecompendio._name = generar_nombre("archivocompendio_", newfilecompendio._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de compendio solo en .doc, docx, pdf, zip, rar"})
                        else:
                            return JsonResponse( {"result": "bad", "mensaje": u"Error, archivo del compendio original es obligatorio."})

                        if 'archivo_logo' in request.FILES:
                            archivo_logo = request.FILES['archivo_logo']
                            if archivo_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd = archivo_logo._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".pdf" or ext == ".PDF":
                                    archivo_logo._name = generar_nombre("archivologocompendio_", archivo_logo._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo es obligatorio."})

                        if 'archivo_sin_logo' in request.FILES:
                            archivo_sin_logo = request.FILES['archivo_sin_logo']
                            if archivo_sin_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd1 = archivo_sin_logo._name
                                ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                    archivo_sin_logo._name = generar_nombre("archivosinlogocompendio_", archivo_sin_logo._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})

                        compendio = CompendioSilaboSemanal(silabosemanal=silabosemanal,
                                                           estado_id=2,
                                                           descripcion=f.cleaned_data['observacion'],
                                                           archivocompendio = newfilecompendio,
                                                           archivo_logo=archivo_logo,
                                                           archivo_sin_logo=archivo_sin_logo,
                                                           tiporecurso_id=3)
                        compendio.save(request)
                        historial = HistorialaprobacionCompendio(compendio=compendio,
                                                                 estado_id=2,
                                                                 observacion="CARGADO POR CRAI")
                        historial.save(request)
                        log(u'Ingresa compendio crai : %s %s' % (compendio, compendio.silabosemanal), request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos %s'%ex})

            elif action == 'editcompendiovirtual':
                try:
                    compendio = CompendioSilaboSemanal.objects.get(pk=int(encrypt(request.POST['id'])))
                    lista_formato = []
                    lista_extension = []
                    if compendio.mis_formatos(periodo):
                        for format in compendio.mis_formatos(periodo):
                            lista_formato.append(format.nombre)
                            for extension in format.extension.all():
                                lista_extension.append(extension.nombre)
                    newfilecompendio=None
                    archivo_logo = None
                    archivo_sin_logo = None
                    form = CraiRecursoSilaboSemanalForm(request.POST, request.FILES)
                    if form.is_valid():
                        compendio.descripcion = form.cleaned_data['observacion']
                        if 'archivooriginal' in request.FILES:
                            newfilecompendio = request.FILES['archivooriginal']
                            if newfilecompendio.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesguiad = newfilecompendio._name
                                ext = newfilesguiad[newfilesguiad.rfind("."):]
                                ext = ext.lower()
                                if lista_extension:
                                    if ext in lista_extension:
                                        newfilecompendio._name = generar_nombre("archivocompendio_", newfilecompendio._name)
                                        compendio.archivocompendio = newfilecompendio
                                    else:
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"Error, archivo de compendio solo en %s" % (
                                                                 lista_extension)})
                                elif ext == ".pdf" or ext == ".PDF":
                                    newfilecompendio._name = generar_nombre("archivocompendio_", newfilecompendio._name)
                                    compendio.archivocompendio = newfilecompendio
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de compendio solo en .doc, docx, pdf, zip, rar"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio original es obligatorio."})

                        if 'archivo_logo' in request.FILES:
                            archivo_logo = request.FILES['archivo_logo']
                            if archivo_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd = archivo_logo._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".pdf" or ext == ".PDF":
                                    archivo_logo._name = generar_nombre("archivologocompendio_", archivo_logo._name)
                                    compendio.archivo_logo = archivo_logo
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio con logo es obligatorio."})

                        if 'archivo_sin_logo' in request.FILES:
                            archivo_sin_logo = request.FILES['archivo_sin_logo']
                            if archivo_sin_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd1 = archivo_sin_logo._name
                                ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                    archivo_sin_logo._name = generar_nombre("archivosinlogocompendio_", archivo_sin_logo._name)
                                    compendio.archivo_sin_logo = archivo_sin_logo
                                else:
                                    return JsonResponse({"result": "bad","mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})

                        compendio.save(request)
                        log(u'Edita compendio crai : %s %s' % (compendio,compendio.silabosemanal), request, "edit")
                        return JsonResponse({"result": "ok"})

                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addguiaestudiantevirtual':
                try:
                    silabosemanal=SilaboSemanal.objects.get(id=int(encrypt(request.POST['id'])))
                    lista_formato = []
                    lista_extension = []
                    if ConfiguracionRecurso.objects.filter(status=True, tiporecurso=2,
                                                           carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                           periodo=periodo).exists():
                        configuracion = ConfiguracionRecurso.objects.filter(status=True, tiporecurso=2,
                                                                            carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                            periodo=periodo)[0]
                        for format in configuracion.formato.all():
                            lista_formato.append(format.nombre)
                            for extension in format.extension.all():
                                lista_extension.append(extension.nombre)
                    f = CraiRecursoSilaboSemanalForm(request.POST, request.FILES)
                    if f.is_valid():
                        newfileguia=None
                        archivo_sin_logo=None
                        archivo_logo=None
                        if 'archivooriginal' in request.FILES:
                            newfileguia = request.FILES['archivooriginal']
                            if newfileguia.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesguiad = newfileguia._name
                                ext = newfilesguiad[newfilesguiad.rfind("."):]
                                ext = ext.lower()
                                if lista_extension:
                                    if ext in lista_extension:
                                        newfileguia._name = generar_nombre("archivoguiaestudiante_", newfileguia._name)
                                    else:
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"Error, archivo de compendio solo en %s" % (lista_extension)})
                                elif ext == ".pdf" or ext == ".PDF":
                                    newfileguia._name = generar_nombre("archivoguiaestudiante_", newfileguia._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de guía del estudiante solo en .pdf"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de la guía original es obligatorio."})

                        if 'archivo_logo' in request.FILES:
                            archivo_logo = request.FILES['archivo_logo']
                            if archivo_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd = archivo_logo._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".pdf" or ext == ".PDF":
                                    archivo_logo._name = generar_nombre("archivologoguiaestudiante_", archivo_logo._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, archivo del compendio con logo es obligatorio."})

                        if 'archivo_sin_logo' in request.FILES:
                            archivo_sin_logo = request.FILES['archivo_sin_logo']
                            if archivo_sin_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd1 = archivo_sin_logo._name
                                ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                    archivo_sin_logo._name = generar_nombre("archivosinlogoguiaestudiante_", archivo_sin_logo._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})

                        guiaestudiante = GuiaEstudianteSilaboSemanal(silabosemanal=silabosemanal,
                                                                     observacion=f.cleaned_data['observacion'],
                                                                     archivoguiaestudiante=newfileguia,
                                                                     archivo_sin_logo = archivo_sin_logo,
                                                                     archivo_logo=archivo_logo,
                                                                     estado_id=2,
                                                                     tiporecurso_id=2)
                        guiaestudiante.save(request)

                        historial = HistorialaprobacionGuiaEstudiante(
                            guiaestudiante=guiaestudiante,
                            estado_id=2,
                            observacion="CARGADO POR CRAI")
                        historial.save(request)
                        log(u'Ingresa guia estudiante crai : %s %s' % (guiaestudiante, guiaestudiante.silabosemanal), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            elif action == 'editguiaestudiantevirtual':
                try:
                    guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=int(encrypt(request.POST['id'])))
                    lista_formato = []
                    lista_extension = []
                    if guiaestudiante.mis_formatos(periodo):
                        for format in guiaestudiante.mis_formatos(periodo):
                            lista_formato.append(format.nombre)
                            for extension in format.extension.all():
                                lista_extension.append(extension.nombre)
                    form = CraiRecursoSilaboSemanalForm(request.POST, request.FILES)
                    if form.is_valid():
                        guiaestudiante.observacion = form.cleaned_data['observacion']
                        newfileguia=None
                        archivo_logo=None
                        archivo_sin_logo=None
                        if 'archivooriginal' in request.FILES:
                            newfileguia = request.FILES['archivooriginal']
                            if newfileguia.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesguiad = newfileguia._name
                                ext = newfilesguiad[newfilesguiad.rfind("."):]
                                ext = ext.lower()
                                if lista_extension:
                                    if ext in lista_extension:
                                        newfileguia._name = generar_nombre("archivoguiaestudiante_",newfileguia._name)
                                        guiaestudiante.archivoguiaestudiante = newfileguia
                                    else:
                                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de compendio solo en %s" % (lista_extension)})
                                elif ext == ".pdf" or ext == ".PDF":
                                    newfileguia._name = generar_nombre("archivoguiaestudiante_", newfileguia._name)
                                    guiaestudiante.archivoguiaestudiante = newfileguia
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de guía del estudiante solo en .pdf"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo de la guía original es obligatorio."})

                        if 'archivo_logo' in request.FILES:
                            archivo_logo = request.FILES['archivo_logo']
                            if archivo_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd = archivo_logo._name
                                ext = newfilesrubd[newfilesrubd.rfind("."):]
                                if ext == ".pdf" or ext == ".PDF":
                                    archivo_logo._name = generar_nombre("archivologoguiaestudiante_", archivo_logo._name)
                                    guiaestudiante.archivo_logo = archivo_logo
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo del compendio con logo solo en pdf"})
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, archivo del compendio con logo es obligatorio."})

                        if 'archivo_sin_logo' in request.FILES:
                            archivo_sin_logo = request.FILES['archivo_sin_logo']
                            if archivo_sin_logo.size > 50485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                            else:
                                newfilesrubd1 = archivo_sin_logo._name
                                ext = newfilesrubd1[newfilesrubd1.rfind("."):]
                                if ext == ".doc" or ext == ".docx" or ext == ".DOC" or ext == ".DOCX":
                                    archivo_sin_logo._name = generar_nombre("archivosinlogoguiaestudiante_", archivo_sin_logo._name)
                                    guiaestudiante.archivo_sin_logo = archivo_sin_logo
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo del compendio sin logo solo en .doc o .docx"})
                        guiaestudiante.save(request)
                        log(u'Edita guia estudiante crai : %s %s' % (guiaestudiante, guiaestudiante.silabosemanal), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'programanalitico':
                try:
                    data['title'] = u'Gestión de videos'
                    data['c'] = None
                    data['mc'] = None
                    data['carr'] = None
                    data['nivel'] = None
                    if 'c' in request.GET:
                        data['c']=request.GET['c']
                    if 'mc' in request.GET:
                        data['mc']=request.GET['mc']
                    if 'carr' in request.GET:
                        data['carr']=request.GET['carr']
                    if 'nivel' in request.GET:
                        data['nivel']=request.GET['nivel']
                    data['autorprograma'] = autorprograma = AutorprogramaAnalitico.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['programanalitico'] = autorprograma.programaanalitico
                    data['contenido'] = autorprograma.programaanalitico.contenido_program_analitico()
                    return render(request, "adm_gestionvideos/programaanalitico.html", data)
                except Exception as ex:
                    pass

            if action == 'cargavidmagistral':
                try:
                    data['title'] = u'Subir video magistral'
                    data['planificacionmateria'] = VideoMagistralSilaboSemanal.objects.get(pk=int(encrypt(request.GET['idvideo'])))
                    form = AprobarVideoMagistralForm()
                    data['form'] = form
                    return render(request, "adm_gestionvideos/cargavidmagistral.html", data)
                except Exception as ex:
                    pass

            if action == 'videotutor':
                try:
                    data['title'] = u'Gestión de videos'
                    data['pm'] = pm = ProfesorMateria.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['materia'] = pm.materia
                    programanalitico = []
                    contenido = []
                    if pm.materia.tiene_silabo_semanal():
                        silabo = pm.materia.silabo_actual()
                        programanalitico = silabo.programaanaliticoasignatura
                        contenido = programanalitico.contenido_program_analitico()
                    data['programanalitico'] = programanalitico
                    data['contenido'] = contenido
                    return render(request, "adm_gestionvideos/videostutor.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobar_videotema':
                try:
                    data['title'] = u'Aprobar video del tema: '
                    data['autorprograma'] = autorprograma = AutorprogramaAnalitico.objects.get(status=True, pk=int(encrypt(request.GET['autor'])))
                    data['tema'] = tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_gestionvideos/aprobar_video.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobar_unidades':
                try:
                    data['title'] = u'Aprobar Unidades, Temas y Subtemas de los videos cargados: '
                    data['autorprograma'] = autorprograma = AutorprogramaAnalitico.objects.get(status=True, pk=int(encrypt(request.GET['autor'])))
                    data['unidad'] = unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_gestionvideos/aprobar_unidades.html", data)
                except Exception as ex:
                    pass

            elif action == 'habilitar_videotema':
                try:
                    data['title'] = u'Habilitar video del tema: '
                    data['autorprograma'] = autorprograma = AutorprogramaAnalitico.objects.get(status=True, pk=int(encrypt(request.GET['autor'])))
                    data['tema'] = tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_gestionvideos/habilitar_video.html", data)
                except Exception as ex:
                    pass

            elif action == 'habilitar_unidades':
                try:
                    data['title'] = u'Habilitar video de los temas y subtemas de la unidad: '
                    data['autorprograma'] = autorprograma = AutorprogramaAnalitico.objects.get(status=True, pk=int(encrypt(request.GET['autor'])))
                    data['unidad'] = unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_gestionvideos/habilitar_unidades.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalles_video_unidad':
                try:
                    data['title'] = u'Detalle video unidad'
                    data['unidad'] =  unidad = UnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    data['videos'] = unidad.videounidadresultadoprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['recursos'] = unidad.recursounidadprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.GET['iduap']))
                    data['videos_eliminados']=VideoUnidadResultadoProgramaAnaliticoEliminado.objects.filter(unidad=unidad)
                    data['recursos_eliminados'] = RecursoUnidadProgramaAnaliticoEliminado.objects.filter(unidad=unidad)
                    return render(request, "adm_gestionvideos/detalles_video_unidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalles_video_tema':
                try:
                    data['title'] = u'Detalle video tema'
                    data['tema'] = tema = TemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    data['videos'] = tema.videotemaprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['recursos'] = tema.recursotemaprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['videos_eliminados'] = VideoTemaProgramaAnaliticoEliminado.objects.filter(tema=tema)
                    data['recursos_eliminados'] = RecursoTemaProgramaAnaliticoEliminado.objects.filter(tema=tema)
                    data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.GET['idup']))
                    return render(request, "adm_gestionvideos/detalles_video_tema.html", data)
                except Exception as ex:
                    print(str(ex))
                    pass

            elif action == 'solicitudvideomagistral':
                try:
                    data['title'] = u'Solicitudes de videos magistrales'
                    search = None
                    idcar = None
                    idcor = None
                    idsem = None
                    idnivel = None
                    videosmagistrales = None
                    idestado = 1
                    videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado,status=True,
                                                                                   presentacion_validado=True,
                                                                                   silabosemanal__silabo__materia__nivel__periodo=periodo,
                                                                                   ).order_by('silabosemanal__numsemana', '-fecha_creacion').distinct()
                    if 'idest' in request.GET:
                        idestado = int(request.GET['idest'])
                        if idestado>0:
                            videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, status=True,
                                                                                       presentacion_validado=True,
                                                                                           silabosemanal__silabo__materia__nivel__periodo=periodo,
                                                                                       ).order_by('silabosemanal__numsemana', '-fecha_creacion').distinct()
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            videosmagistrales = videosmagistrales.filter((Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[0]) &
                                                                          Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[1])) | (
                                    Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[0]) &
                                    Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[1])) |
                                    (Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=s[0]) &
                                     Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido2__icontains=s[1])))
                        else:
                            videosmagistrales = videosmagistrales.filter(Q(
                                silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=search))

                    if 'idcor' in request.GET:
                        idcor = int(request.GET['idcor'])
                        if idcor >0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__malla__carrera__coordinacion=idcor)
                            data['carreras'] = Carrera.objects.filter(coordinacion__id=idcor,modalidad=3).distinct()
                    else:
                        data['carreras'] = None
                    if 'idcar' in request.GET:
                        idcar = int(request.GET['idcar'])
                        if idcar>0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__malla__carrera_id=idcar)
                        data['semanas'] = videosmagistrales.values_list('silabosemanal__numsemana').distinct()
                    else:
                        data['semanas'] = None
                    if 'idsem' in request.GET:
                        idsem=int(request.GET['idsem'])
                        if idsem>0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__numsemana = idsem)

                    if 'idnivel' in request.GET:
                        idnivel = int(request.GET['idnivel'])
                        if idnivel > 0:
                            videosmagistrales = videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__nivelmalla_id=idnivel)
                            # if 'idcor' in request.GET:
                            #     idcor = int(request.GET['idcor'])
                            #     if (('idcar' not in request.GET and 'idsem' in request.GET) or ('idcar' in request.GET and 'idsem' in request.GET)):
                            #         if 'idcar' in request.GET:
                            #             idcar = int(request.GET['idcar'])
                            #         else:
                            #             idcar=0
                            #         if 'idsem' in request.GET:
                            #             idsem = int(request.GET['idsem'])
                            #         else:
                            #             idsem=0
                            #         if idcar == 0 and idsem != 0:
                            #             videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, silabosemanal__numsemana=idsem, status=True, presentacion_validado=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                            #         else:
                            #             if idsem == 0 and idcar != 0:
                            #                 videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, silabosemanal__silabo__materia__asignaturamalla__malla__carrera_id=idcar, status=True, presentacion_validado=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                            #             else:
                            #                 videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, silabosemanal__silabo__materia__asignaturamalla__malla__carrera_id=idcar,silabosemanal__numsemana=idsem, status=True, presentacion_validado=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                            #     else:
                            #         videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(silabosemanal__silabo__materia__asignaturamalla__malla__carrera__coordinacion=idcor, estado_id=idestado, status=True, presentacion_validado=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                            # else:
                            #     videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, status=True, presentacion_validado=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                            # else:
                            #     videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, status=True).order_by('silabosemanal__numsemana', '-fecha_creacion')
                    # if 'idcor' in request.GET:
                    #     idcor=request.GET['idcor']
                    #     data['carreras'] = Carrera.objects.filter(coordinacion_id=idcor).distinct()
                    #
                    # if 'idcar' in request.GET:
                    #     data['semanas'] = videosmagistrales.values_list('silabosemanal__numsemana').distinct()
                    # else:
                    #     data['semanas'] = None
                    data['niveles']=NivelMalla.objects.filter(status=True)
                    paging = MiPaginador(videosmagistrales, 25)
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
                    data['idcar'] = int(idcar) if idcar else ""
                    data['idsem'] = int(idsem) if idsem else ""
                    data['idest'] = int(idestado)
                    data['idcor'] = int(idcor) if idcor else ""
                    data['idnivel'] = int(idnivel) if idnivel else ""
                    data['coordinaciones'] = Coordinacion.objects.filter(id__in=[1, 2, 3, 4, 5])
                    data['listavideosmagistrales'] = page.object_list
                    data['estados']=Estado.objects.filter(status=True).exclude(id=5)
                    return render(request, "adm_gestionvideos/solicitudvideomagistral.html", data)
                except Exception as ex:
                    pass


            elif action == 'solicitudvideomagistralreporte':
                try:
                    data['title'] = u'Solicitudes de videos magistrales'
                    search = None
                    idcar = None
                    idcor = None
                    idsem = None
                    idnivel = None
                    videosmagistrales = None
                    idestado = 1
                    videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado,status=True,
                                                                                   presentacion_validado=True
                                                                                   ).order_by('silabosemanal__numsemana', '-fecha_creacion')
                    if 'idest' in request.GET:
                        idestado = int(request.GET['idest'])
                        if idestado>0:
                            videosmagistrales = VideoMagistralSilaboSemanal.objects.filter(estado_id=idestado, status=True,
                                                                                       presentacion_validado=True
                                                                                       ).order_by('silabosemanal__numsemana', '-fecha_creacion')
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            videosmagistrales = videosmagistrales.filter((Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[0]) &
                                                                          Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[1])) | (
                                    Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[0]) &
                                    Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[1])) |
                                    (Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=s[0]) &
                                     Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido2__icontains=s[1])))
                        else:
                            videosmagistrales = videosmagistrales.filter(Q(
                                silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=search) | Q(
                                silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=search))

                    if 'idcor' in request.GET:
                        idcor = int(request.GET['idcor'])
                        if idcor >0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__malla__carrera__coordinacion=idcor)
                            data['carreras'] = Carrera.objects.filter(coordinacion__id=idcor,modalidad=3).distinct()
                    else:
                        data['carreras'] = None
                    if 'idcar' in request.GET:
                        idcar = int(request.GET['idcar'])
                        if idcar>0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__malla__carrera_id=idcar)
                        data['semanas'] = videosmagistrales.values_list('silabosemanal__numsemana').distinct()
                    else:
                        data['semanas'] = None
                    if 'idsem' in request.GET:
                        idsem=int(request.GET['idsem'])
                        if idsem>0:
                            videosmagistrales=videosmagistrales.filter(silabosemanal__numsemana = idsem)

                    if 'idnivel' in request.GET:
                        idnivel = int(request.GET['idnivel'])
                        if idnivel > 0:
                            videosmagistrales = videosmagistrales.filter(silabosemanal__silabo__materia__asignaturamalla__nivelmalla_id=idnivel)

                    borders = Borders()

                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_videos' + random.randint(
                        1, 10000).__str__() + '.xls'
                    ws.col(0).width = 10000
                    ws.col(1).width = 10000
                    ws.col(7).width = 10000
                    ws.col(9).width = 10000
                    ws.col(10).width = 10000
                    ws.col(11).width = 5000

                    row_num = 0
                    ws.write(row_num, 0, 'Asignatura', encabesado_tabla)
                    ws.write(row_num, 1, 'Profesor', encabesado_tabla)
                    ws.write(row_num, 2, 'Carrera', encabesado_tabla)
                    ws.write(row_num, 3, 'Nivel', encabesado_tabla)
                    ws.write(row_num, 4, 'Paralelo', encabesado_tabla)
                    ws.write(row_num, 5, 'Fecha', encabesado_tabla)
                    ws.write(row_num, 6, 'Semana', encabesado_tabla)
                    ws.write(row_num, 7, 'Unidad', encabesado_tabla)
                    ws.write(row_num, 8, 'Tipo de grabación', encabesado_tabla)
                    ws.write(row_num, 9, 'Estado', encabesado_tabla)
                    ws.write(row_num, 10, 'Descripción', encabesado_tabla)
                    ws.write(row_num, 11, 'Estado video', encabesado_tabla)

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    i = 0
                    row_num = 1
                    campo1 = ''

                    for video in videosmagistrales:

                        unidades = video.silabosemanal.unidades_silabosemanal()
                        for uni in unidades:
                            campouni = uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden
                            campo1 = str(video.silabosemanal.silabo.profesor)
                            campo2 = str(video.silabosemanal.silabo.materia.asignatura.nombre)
                            campo3 = str(video.silabosemanal.silabo.materia.asignaturamalla.nivelmalla)
                            campocar = str(video.silabosemanal.silabo.materia.asignaturamalla.malla.carrera)

                            campo4 = str(video.silabosemanal.silabo.materia.paralelo)
                            campo5 = (video.fecha_creacion)
                            campo6 = str(video.silabosemanal.numsemana)
                            campo7 = video.get_tipograbacion_display()
                            tipog = str(video.tipograbacion)
                            campo9 = str(video.descripcion)
                            campocarrera = str(video.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.nombre)

                            if video.estado_id == 1:
                                campo8 = str(video.estado)
                            elif video.estado_id == 2:
                                campo8 = str(video.estado)
                            elif video.estado_id == 3:
                                 campo8 = str(video.estado)
                            elif video.estado_id == 4:
                                campo8 = str(video.estado)

                            if video.url:
                                campo10 = 'RECIBIDO Y EDITADO'
                            elif tipog == '2':
                                campo10 = ''
                            else:
                                campo10 = 'NO RECIBIDO'

                            ws.write(row_num, 0, campo2, normal)
                            ws.write(row_num, 1, campo1, normal)
                            ws.write(row_num, 2, campocarrera, normal)
                            ws.write(row_num, 3, campo3, normal)
                            ws.write(row_num, 4, campo4, normal)
                            ws.write(row_num, 5, campo5, date_format)
                            ws.write(row_num, 6, campo6, normal)

                            ws.write(row_num, 7, campouni, normal)
                            ws.write(row_num, 8, campo7, normal)
                            ws.write(row_num, 9, campo8, normal)
                            ws.write(row_num, 10, campo9, normal)
                            ws.write(row_num, 11, campo10, normal)


                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass




            elif action == 'detalles_video_subtema':
                try:
                    data['title'] = u'Detalle video sub tema'
                    data['subtema']= subtema = SubtemaUnidadResultadoProgramaAnalitico.objects.get(pk=int(request.GET['id']))
                    data['videos'] = subtema.videosubtemaprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['autorprograma'] = AutorprogramaAnalitico.objects.get(pk=int(request.GET['idup']))
                    data['recursos'] = subtema.recursosubtemaprogramaanalitico_set.filter(status=True).order_by('orden')
                    data['videos_eliminados'] = VideoSubTemaProgramaAnaliticoEliminado.objects.filter(subtema=subtema)
                    data['recursos_eliminados'] = RecursoSubTemaProgramaAnaliticoEliminado.objects.filter(subtema=subtema)
                    return render(request, "adm_gestionvideos/detalles_video_subtema.html", data)
                except Exception as ex:
                    pass

            elif action == 'materias_recursos':
                try:
                    data['carreras_select'] = carreras=Carrera.objects.filter(status=True, modalidad=3, coordinacion__id__in=[1, 2, 3, 4, 5])
                    data['materias_select'] = materias=Materia.objects.filter(status=True,nivel__periodo__visible=True,
                                                    nivel__periodo=periodo,
                                                    asignaturamalla__malla__carrera__modalidad=3,
                                                    asignaturamalla__malla__carrera__id__in=carreras.values_list('id',flat=True))
                    data['profesor_select'] = Profesor.objects.filter(status=True, id__in=materias.values_list(
                        'profesormateria__profesor_id', flat=True))
                    search=None
                    idcarr=None
                    idmat=None
                    iddoc=None
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            materias = materias.filter(Q(asignatura__nombre__icontains=s[0]) & Q(asignatura__nombre__icontains=s[1]))
                        else:
                            materias = materias.filter(Q(asignatura__nombre__icontains=search))
                    if 'idcarr' in request.GET:
                        idcarr=int(request.GET['idcarr'])
                        if idcarr>0:
                            materias=materias.filter(asignaturamalla__malla__carrera_id=idcarr)
                    if 'idmat' in request.GET:
                        idmat=int(request.GET['idmat'])
                        if idmat>0:
                            materias=materias.filter(id=idmat)
                    if 'iddoc' in request.GET:
                        iddoc = int(request.GET['iddoc'])
                        if iddoc > 0:
                            idsmate=ProfesorMateria.objects.values_list('materia_id',flat=True).filter(status=True, activo=True, profesor_id=iddoc,materia__nivel__periodo=periodo)
                            materias = materias.filter(id__in=idsmate)
                    paging = MiPaginador(materias, 20)
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
                    data['materias']= page.object_list
                    data['search'] = search if search else ""
                    data['idcarr_select'] = idcarr if idcarr else ""
                    data['idmat_select'] = idmat if idmat else ""
                    data['iddoc_select'] = iddoc if iddoc else ""
                    return render(request, "adm_gestionvideos/materias_recursos.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'reporte_materias_recursos':

                try:
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    if materia.silabo_set.filter(status=True, codigoqr=True).exists():
                        silabocab = materia.silabo_set.filter(status=True, codigoqr=True).latest(
                            'id')
                        silabosemanal = silabocab.silabosemanal_set.filter(status=True) if silabocab else None
                        listado = [2, 4, 5]
                    else:
                        raise NameError("No existe un silabo aprobado en la materia seleccionada.")

                    borders = Borders()

                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=detalle_recursos_profesores' + random.randint(
                        1, 10000).__str__() + '.xls'
                    ws.col(1).width = 10000
                    ws.col(3).width = 10000
                    ws.col(2).width = 10000

                    ws.col(7).width = 10000
                    ws.col(8).width = 15000
                    ws.col(9).width = 5000
                    ws.col(10).width = 10000
                    ws.col(11).width = 5000
                    ws.col(12).width = 10000
                    row_num = 0
                    ws.write(row_num, 0, 'Asignatura', encabesado_tabla)
                    ws.write(row_num, 1, 'Profesor', encabesado_tabla)
                    ws.write(row_num, 2, 'Estado GUIA DEL ESTUDIANTE', encabesado_tabla)
                    ws.write(row_num, 3, 'Descripción GUIA DEL ESTUDIANTE', encabesado_tabla)
                    ws.write(row_num, 4, 'Estado COMPENDIO', encabesado_tabla)
                    ws.write(row_num, 5, 'Descripción COMPENDIO', encabesado_tabla)
                    ws.write(row_num, 6, 'Unidad', encabesado_tabla)
                    ws.write(row_num, 7, 'Descripcion Unidad', encabesado_tabla)
                    ws.write(row_num, 8, 'Semana', encabesado_tabla)
                    ws.write(row_num, 9, 'Fecha desde', encabesado_tabla)
                    ws.write(row_num, 10, 'Fecha hasta', encabesado_tabla)
                    ws.write(row_num, 11, 'Tema', encabesado_tabla)
                    ws.write(row_num, 12, 'Subtema', encabesado_tabla)


                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    i = 0
                    row_num = 1
                    campo1 = ''
                    campo1 = str(silabocab.materia.profesor_principal)
                    for semana in silabosemanal:
                        unidades = semana.unidades_silabosemanal()
                        profe = str(silabocab.profesor)
                        materia = str(silabocab.materia.asignaturamalla.asignatura.nombre)
                        numsemana = str(semana.numsemana)
                        fechadesde = semana.fechainiciosemana
                        fechahasta = semana.fechafinciosemana
                        esta = semana.guiaestudiante_semanales
                        estadose = semana.guiaestudiante_semanales_estado(listado)
                        if estadose:
                            cal = str(estadose.estado)
                            d = str(estadose.observacion)
                        else:
                            cal = ""
                            d = ""




                        estadoestudiantes = semana.compendio_semanales_estado(listado)

                        if estadoestudiantes:
                            est = str(estadoestudiantes.estado)
                            e = str(estadoestudiantes.descripcion)
                        else:
                            est = ""
                            e = ""

                        for uni in unidades:

                            campo = uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden
                            campodescripcion = str(uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.descripcion)
                            unidadid = uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.id
                            arr = semana.temas_silabosemanal(unidadid)

                            for a in arr:
                                ca = str(a.temaunidadresultadoprogramaanalitico.descripcion)
                                sub = a.temaunidadresultadoprogramaanalitico
                                subtema = semana.subtemas_silabosemanal(sub)
                                arr = [f'{su.subtemaunidadresultadoprogramaanalitico.orden}{"."} {su.subtemaunidadresultadoprogramaanalitico.descripcion}' for su in subtema]
                                str_j= ' - '.join(arr)




                            ws.write(row_num, 0, materia, normal)
                            ws.write(row_num, 1, profe, normal)
                            ws.write(row_num, 2, cal, normal)
                            ws.write(row_num, 3, d, normal)
                            ws.write(row_num, 4, est, normal)
                            ws.write(row_num, 5, e, normal)
                            ws.write(row_num, 6, campo, normal)
                            ws.write(row_num, 7, campodescripcion, normal)
                            ws.write(row_num, 8, numsemana, normal)
                            ws.write(row_num, 9, fechadesde, date_format)
                            ws.write(row_num, 10, fechahasta, date_format)
                            ws.write(row_num, 11, ca, normal)
                            ws.write(row_num, 12, str_j, normal)


                        row_num += 1





                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_materias_recursos_general':

                try:
                    idcarr = None
                    idcarr = int(request.GET['idcarr'])
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=detalle_recursos_profesores' + random.randint(
                        1, 10000).__str__() + '.xls'
                    ws.col(1).width = 10000
                    ws.col(3).width = 10000
                    ws.col(2).width = 10000

                    ws.col(7).width = 10000
                    ws.col(8).width = 15000
                    ws.col(9).width = 5000
                    ws.col(10).width = 10000
                    ws.col(11).width = 5000
                    ws.col(12).width = 10000
                    row_num = 0

                    ws.write(row_num, 0, 'Carrera', encabesado_tabla)
                    ws.write(row_num, 1, 'Asignatura', encabesado_tabla)
                    ws.write(row_num, 2, 'Profesor', encabesado_tabla)
                    ws.write(row_num, 3, 'Estado GUIA DEL ESTUDIANTE', encabesado_tabla)
                    ws.write(row_num, 4, 'Descripción GUIA DEL ESTUDIANTE', encabesado_tabla)
                    ws.write(row_num, 5, 'Estado COMPENDIO', encabesado_tabla)
                    ws.write(row_num, 6, 'Descripción COMPENDIO', encabesado_tabla)
                    ws.write(row_num, 7, 'Unidad', encabesado_tabla)
                    ws.write(row_num, 8, 'Descripcion Unidad', encabesado_tabla)
                    ws.write(row_num, 9, 'Paralelo', encabesado_tabla)
                    ws.write(row_num, 10, 'Semana', encabesado_tabla)
                    ws.write(row_num, 11, 'Fecha desde', encabesado_tabla)
                    ws.write(row_num, 12, 'Fecha hasta', encabesado_tabla)
                    ws.write(row_num, 13, 'Tema', encabesado_tabla)
                    ws.write(row_num, 14, 'Subtema', encabesado_tabla)

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'


                    materias = Materia.objects.filter(asignaturamalla__malla__carrera_id=idcarr, status=True, nivel__periodo=periodo).distinct()
                    i = 0
                    row_num = 1
                    for materia in materias:

                        if materia.silabo_set.filter(status=True, codigoqr=True).exists():
                            silabocab = materia.silabo_set.filter(status=True, codigoqr=True).latest('id')
                            silabosemanal = silabocab.silabosemanal_set.filter(status=True).distinct() if silabocab else None
                            listado = [2, 4, 5]

                        for semana in silabosemanal:
                            profe = str(silabocab.profesor)
                            mat = str(silabocab.materia.asignaturamalla.asignatura.nombre)
                            paralelo = str(silabocab.materia.paralelo)
                            carr = str(silabocab.materia.asignaturamalla.malla.carrera)

                            numsemana = str(semana.numsemana)
                            fechadesde = semana.fechainiciosemana
                            fechahasta = semana.fechafinciosemana
                            estadose = semana.guiaestudiante_semanales_estado(listado)
                            cal = ""
                            d = ""
                            est = ""
                            e = ""
                            if estadose:
                                cal = str(estadose.estado)
                                d = str(estadose.observacion)
                            else:
                                cal = ""
                                d = ""

                            estadoestudiantes = semana.compendio_semanales_estado(listado)

                            if estadoestudiantes:
                                est = str(estadoestudiantes.estado)
                                e = str(estadoestudiantes.descripcion)
                            else:
                                est = ""
                                e = ""
                            unidades = semana.unidades_silabosemanal()
                            if unidades:
                                for uni in unidades:

                                    campo = uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden
                                    campodescripcion = str(
                                        uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.descripcion)
                                    unidadid = uni.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.id
                                    arr = semana.temas_silabosemanal(unidadid)

                                    for a in arr:
                                        ca = str(a.temaunidadresultadoprogramaanalitico.descripcion)
                                        sub = a.temaunidadresultadoprogramaanalitico
                                        subtema = semana.subtemas_silabosemanal(sub)
                                        if subtema:
                                            arr = [
                                                f'{su.subtemaunidadresultadoprogramaanalitico.orden}{"."} {su.subtemaunidadresultadoprogramaanalitico.descripcion}'
                                                for su in subtema]
                                            str_j = ' - '.join(arr)
                                        else:
                                            str_j = ""
                                    ws.write(row_num, 0, carr, normal)
                                    ws.write(row_num, 1, mat, normal)
                                    ws.write(row_num, 2, profe, normal)
                                    ws.write(row_num, 3, cal, normal)
                                    ws.write(row_num, 4, d, normal)
                                    ws.write(row_num, 5, est, normal)
                                    ws.write(row_num, 6, e, normal)
                                    ws.write(row_num, 7, campo, normal)
                                    ws.write(row_num, 8, campodescripcion, normal)
                                    ws.write(row_num, 9, paralelo, normal)
                                    ws.write(row_num, 10, numsemana, normal)
                                    ws.write(row_num, 11, fechadesde, date_format)
                                    ws.write(row_num, 12, fechahasta, date_format)
                                    ws.write(row_num, 13, ca, normal)
                                    ws.write(row_num, 14, str_j, normal)


                                    row_num += 1


                            else:
                                campo = ""
                                campodescripcion = ""
                                ca = ""
                                str_j = ""

                                ws.write(row_num, 0, carr, normal)
                                ws.write(row_num, 1, mat, normal)
                                ws.write(row_num, 2, profe, normal)
                                ws.write(row_num, 3, cal, normal)
                                ws.write(row_num, 4, d, normal)
                                ws.write(row_num, 5, est, normal)
                                ws.write(row_num, 6, e, normal)
                                ws.write(row_num, 7, campo, normal)
                                ws.write(row_num, 8, campodescripcion, normal)
                                ws.write(row_num, 9, paralelo, normal)
                                ws.write(row_num, 10, numsemana, normal)
                                ws.write(row_num, 11, fechadesde, date_format)
                                ws.write(row_num, 12, fechahasta, date_format)
                                ws.write(row_num, 13, ca, normal)
                                ws.write(row_num, 14, str_j, normal)
                                row_num += 1








                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_estado_material':
                try:
                    __author__ = 'Unemi'

                    #coordinacion = request.GET  ['coordinacion']
                    # periodo_nombre = request.GET['periodo_nombre']

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('estado_material')
                    ws.set_column(0, 10, 30)
                    formatotitulo = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'middle',
                         'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:D1', 'REPORTE DE ESTADOS DE MATERIALES', formatotitulo)
                    ws.merge_range('E1:F1', str(periodo), formatoceldaleft)
                    ws.merge_range('G1:H1', str(periodo), formatoceldaleft)

                    ws.write(1, 0, 'UNIDAD', formatoceldacab)
                    ws.write(1, 1, 'DESCRIPCIÓN UNIDAD', formatoceldacab)
                    ws.write(1, 2, 'PROFESOR', formatoceldacab)
                    ws.write(1, 3, 'ASIGNATURA', formatoceldacab)
                    ws.write(1, 4, 'SEMANA', formatoceldacab)
                    ws.write(1, 5, 'TEMA', formatoceldacab)
                    ws.write(1, 6, 'SUBTEMA', formatoceldacab)
                    ws.write(1, 7, 'ESTADO', formatoceldacab)

                    workbook.close()
                    output.seek(0)
                    filename = 'Estado de material.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            elif action == 'cargar_coordinacion':
                try:
                    lista = []
                    coordinaciones = Coordinacion.objects.filter(status=True).distinct()

                    for coordinacion in coordinaciones:
                        if not buscar_dicc(lista, 'id', coordinacion.id):
                            lista.append({'id': coordinacion.id, 'nombre': coordinacion.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_carrera':
                try:
                    lista = []
                    carreras = Carrera.objects.filter(status=True, coordinacion__id__in=[1, 2, 3, 4, 5])

                    for carrera in carreras:
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': carrera.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listar_recursossilabos':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    if materia.silabo_set.filter(status=True,codigoqr=True).exists():
                        data['silabocab'] = silabocab = materia.silabo_set.filter(status=True,codigoqr=True).latest('id')
                        data['silabosemanal'] = silabocab.silabosemanal_set.filter(status=True) if silabocab else None
                        data['lista_estado']=[1,2,4,5]
                        return render(request, "adm_gestionvideos/listar_recursossilabos.html", data)
                    else:
                        raise NameError("No existe un silabo aprobado en la materia seleccionada.")
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s"%ex})
                    pass

            elif action == 'addsolicitudvideomagistral':
                try:
                    data['title'] = u'Adicionar video magistral'
                    form = VideoMagistralSilaboSemanalAdminForm()
                    data['form'] = form
                    return render(request, "adm_gestionvideos/addsolicitudvideomagistral.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscar_carrera':
                try:

                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 1:
                        carreras = Carrera.objects.filter(Q(nombre__icontains=q) | Q(nombrevisualizar__icontains=s[0]), status=True, modalidad=3, )
                    else:
                        carreras = Carrera.objects.filter(Q(nombre__icontains=q) | Q(nombrevisualizar__icontains=s[0]), status=True, modalidad=3, ).distinct()[:70]

                    data = {"result": "ok","results": [{"id": x.id, "name": x.nombre_mostrarc()} for x in carreras]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            elif action == 'buscar_materia':
                try:

                    if 'id_carr' in request.GET:
                        if int(request.GET['id_carr']) > 0:
                            carrera = Carrera.objects.get(pk=request.GET['id_carr'])
                        else:
                            carrera = None
                    else:
                        carrera = None
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                    else:
                        q = ''
                    s = q.split(" ")
                    if s.__len__() == 1:
                        if carrera:
                            materias = Materia.objects.filter(
                                Q(asignatura__nombre__icontains=q) | Q(asignatura__nombre__icontains=s[0]),
                                status=True, nivel__periodo=periodo,
                                asignaturamalla__malla__carrera__modalidad=3,asignaturamalla__malla__carrera= carrera).distinct()[:70]

                        else:
                            materias = Materia.objects.filter(Q(asignatura__nombre__icontains=q) | Q(asignatura__nombre__icontains=s[0]),
                                   status=True,nivel__periodo=periodo,asignaturamalla__malla__carrera__modalidad=3 ).distinct()[:70]
                    else:
                        materias = Materia.objects.filter((Q(asignatura__nombre__icontains=s[0])& Q(asignatura__nombre__icontains=s[1])),
                                                          status = True,
                                                            nivel__periodo = periodo,
                                                            asignaturamalla__malla__carrera__modalidad = 3).distinct()[:70]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.nombre_mostrar()} for x in materias]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'obtener_semanas':
                try:
                    materia = Materia.objects.get(pk=request.GET['id'])
                    lista = []
                    for silabosemanal1 in SilaboSemanal.objects.filter(status=True, silabo__materia=materia,silabo__status=True).distinct():
                        lista.append([silabosemanal1.id, u'%s' % silabosemanal1.nombre_silabo_semana()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addcompendiovirtual':
                try:
                    data['title'] = u'Adicionar compendio'
                    data['codigosemana'] =silabosemanal= SilaboSemanal.objects.get(pk=encrypt(request.GET['codigosemana']))
                    formato=None
                    if ConfiguracionRecurso.objects.filter(status=True,tiporecurso=2, carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,periodo=periodo).exists():
                        configuracion=ConfiguracionRecurso.objects.filter(status=True,tiporecurso=2, carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,periodo=periodo)[0]
                        formato=configuracion.formato.all()
                    form = CraiRecursoSilaboSemanalForm()
                    form.cambiar_hep_text(formato)
                    data['form'] = form
                    return render(request, "adm_gestionvideos/addcompendiovirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcompendiovirtual':
                try:
                    data['title'] = u'Editar compendio'
                    data['codigosemana'] = silabosemanal = SilaboSemanal.objects.get(pk=encrypt(request.GET['codigosemana']))
                    formato = None
                    data['codigocompendiovirtual'] = compendiovirtual = silabosemanal.compendiosilabosemanal_set.get(pk=encrypt(request.GET['codigocompendiovirtual']))
                    formato=compendiovirtual.mis_formatos(periodo)
                    form = CraiRecursoSilaboSemanalForm(initial={'observacion': compendiovirtual.descripcion})
                    form.cambiar_hep_text(formato)
                    data['form'] = form
                    return render(request, "adm_gestionvideos/editcompendiovirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'addguiaestudiantevirtual':
                try:
                    data['title'] = u'Adicionar guía del estudiante'
                    data['codigosemana'] = silabosemanal = SilaboSemanal.objects.get(pk=encrypt(request.GET['codigosemana']))
                    formato = None
                    if ConfiguracionRecurso.objects.filter(status=True, tiporecurso=3,
                                                           carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                           periodo=periodo).exists():
                        configuracion = ConfiguracionRecurso.objects.filter(status=True, tiporecurso=3,
                                                                            carrera=silabosemanal.silabo.materia.asignaturamalla.malla.carrera,
                                                                            periodo=periodo)[0]
                        formato = configuracion.formato.all()
                    form = CraiRecursoSilaboSemanalForm()
                    form.cambiar_hep_text(formato)
                    data['form'] = form
                    return render(request, "adm_gestionvideos/addguiaestudiantevirtual.html", data)
                except Exception as ex:
                    pass

            elif action == 'editguiaestudiantevirtual':
                try:
                    data['title'] = u'Editar guía del estudiante'
                    data['codigosemana'] = silabosemanal = SilaboSemanal.objects.get(pk=encrypt(request.GET['codigosemana']))
                    formato = None
                    data['codigoguiaestudiantevirtual'] = guiaestudiantevirtual = silabosemanal.guiaestudiantesilabosemanal_set.get(pk=encrypt(request.GET['codigoguiaestudiantevirtual']))
                    formato = guiaestudiantevirtual.mis_formatos(periodo)
                    form = CraiRecursoSilaboSemanalForm(initial={'observacion': guiaestudiantevirtual.observacion})
                    form.cambiar_hep_text(formato)
                    data['form'] = form
                    return render(request, "adm_gestionvideos/editguiaestudiantevirtual.html", data)
                except Exception as ex:
                    pass
            # return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar planificacion semanal modalidad virtual'

                coordinaciones = Coordinacion.objects.filter(carrera__in=miscarreras).distinct()
                codigoscarrera = coordinaciones.values_list('carrera__id', flat=True).filter(status=True)
                modalidadcarrera = Modalidad.objects.all()
                carreras = Carrera.objects.filter(id__in=codigoscarrera)
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                # autores = AutorprogramaAnalitico.objects.filter(periodo=periodo, programaanaliticorelacion__asignaturamalla__malla__carrera__modalidad=3, programaanaliticorelacion__activo=True).distinct()

                coordinacionselect  = modalidadcarreraselect  = carreraselect =nivelselect = 0
                if 'c' in request.GET:
                    coordinacionselect = int(request.GET['c'])

                if 'mc' in request.GET:
                    modalidadcarreraselect = int(request.GET['mc'])

                if 'carr' in request.GET:
                    carreraselect = int(request.GET['carr'])

                if 'nivel' in request.GET:
                    nivelselect = int(request.GET['nivel'])
                autores = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla__malla__carrera__in=miscarreras).order_by('asignatura__nombre')

                if 's' in request.GET:
                    search = request.GET['s']
                    s = search.split(" ")
                    if len(s) == 2:
                        autores = autores.filter((Q(asignatura__nombre__icontains=s[0]) & Q(asignatura__nombre__icontains=s[1])) | (Q(autor__persona__nombres__icontains=s[0]) & Q(autor__persona__nombres__icontains=s[1])) | (Q(autor__persona__apellido1__icontains=s[0]) & Q(autor__persona__apellido2__icontains=s[1])))
                    else:
                        autores = autores.filter(Q(asignatura__nombre__icontains=search)|Q(autor__persona__nombres__icontains=search)| Q(autor__persona__apellido1__icontains=search)| Q(autor__persona__apellido2__icontains=search))

                if modalidadcarreraselect > 0:
                    autores = autores.filter(programaanalitico__asignaturamalla__malla__modalidad_id=modalidadcarreraselect)
                    codigoscarrera = autores.values_list('programaanalitico__asignaturamalla__malla__carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)

                if coordinacionselect > 0:
                    autores = autores.filter(programaanalitico__asignaturamalla__malla__carrera__coordinacion__id=coordinacionselect)
                    codigoscarrera = autores.values_list('programaanalitico__asignaturamalla__malla__carrera__id', flat=True).filter(status=True)
                    carreras = carreras.filter(id__in=codigoscarrera)

                if carreraselect not in codigoscarrera:
                    carreraselect = 0

                if carreraselect > 0:
                    autores = autores.filter(programaanalitico__asignaturamalla__malla__carrera_id=carreraselect)

                if nivelselect > 0:
                    autores = autores.filter(programaanalitico__asignaturamalla__nivelmalla__id=nivelselect)
                paging = MiPaginador(autores, 20)
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
                data['autores'] = page.object_list
                data['search'] = search if search else ""
                data['mid'] = mallaid if mallaid else 0
                data['nid'] = nivelmallaid if nivelmallaid else 0
                data['ids'] = ids
                data['periodo'] = periodo
                data['estados'] = ESTADO_APROBACION_VIRTUAL
                data['coordinacionselect'] = coordinacionselect
                # data['nivelselect'] = nivelselect
                data['coordinaciones'] = coordinaciones
                # data['nivelestitulacion'] = nivelestitulacion
                data['modalidadcarrera'] = modalidadcarrera
                data['modalidadcarreraselect'] = modalidadcarreraselect
                # data['anios'] = anios
                # data['anioselect'] = anioselect
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['nivelselect'] = nivelselect

                #videos de tutores
                tutores = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo=periodo, tipoprofesor_id=8)
                paging = MiPaginador(tutores, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'paget' in request.GET:
                        p = int(request.GET['paget'])
                    else:
                        p = paginasesion
                    try:
                        paget = paging.page(p)
                    except:
                        p = 1
                    paget = paging.page(p)
                except:
                    paget = paging.page(p)
                request.session['paginador'] = p
                data['pagingt'] = paging
                data['rangospagingt'] = paging.rangos_paginado(p)
                data['paget'] = paget
                data['tutores'] = paget.object_list
                data['searcht'] = search if search else ""
                data['mid'] = mallaid if mallaid else 0
                data['nid'] = nivelmallaid if nivelmallaid else 0
                data['ids'] = ids
                data['nivel'] = NivelMalla.objects.filter(status=True)
                return render(request, "adm_gestionvideos/view.html", data)
            except Exception as ex:
                pass
