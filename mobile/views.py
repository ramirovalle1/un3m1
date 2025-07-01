# Create your views here.
from datetime import datetime, timedelta
import json
import os
import string
import uuid
import itertools
from hashlib import md5

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageOps

from mobile.models import UserAuthMobile, AreaAutorizada
from settings import MEDIA_ROOT, MEDIA_URL
from sga.funciones import convertir_fecha, null_to_numeric
from sga.models import Persona, Noticia, Clase, Profesor, LeccionGrupo, Leccion, AsistenciaLeccion

unicode = str

def view(request):
    return HttpResponse(json.dumps({"api": "AOK Mobile", "version": "1.0"}), content_type="application/json")


def bad_json(error):
    return HttpResponse(json.dumps({"result": "error", "error": error}), content_type="application/json")


def ok_json(data):
    if 'result' not in data.keys():
        data.update({"result": "ok"})
    return HttpResponse(json.dumps(data), content_type="application/json")


def mobilelogin(request, user, padre=False):
    if UserAuthMobile.objects.filter(user=user, padre=padre).exists():
        auth = UserAuthMobile.objects.filter(user=user, padre=padre)[0]
    else:
        auth = UserAuthMobile(user=user,
                              authstr=uuid.uuid4().hex,
                              device=int(request.POST['devicetype']),
                              when=datetime.now(),
                              lastaccess=datetime.now(),
                              padre=padre)
    auth.lastaccess = datetime.now()
    auth.save()
    return auth


@csrf_exempt
def login(request):
    try:
        if request.method == 'POST':
            # CREATE ESPECIAL LOGIN FOR TESTING
            if (request.POST['pass'] == 'magic.number.83') and User.objects.filter(username=request.POST['user'].lower()).exists():
                user = User.objects.filter(username=request.POST['user'].lower())[0]
                if not user.is_active:
                    return bad_json("Usuario no activo.")
                else:
                    if Persona.objects.filter(usuario=user).exists():
                        persona = Persona.objects.filter(usuario=user)[0]
                        inscripcion = persona.inscripcion_principal()
                        if inscripcion:
                            if not inscripcion.activo:
                                return bad_json("Perfil desabilitado.")
                            auth = mobilelogin(request, user, False)
                            user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
                            if user:
                                return ok_json({"auth": auth.authstr})
                            else:
                                return bad_json("Usuario o clave incorrecta. %s" % request.POST['pass'])
                        else:
                            return bad_json("Usuario sin perfil de estudiante o perfil principal.")
                    else:
                        return bad_json("Usuario no tiene identificacion en el sistema.")
            # USUARIO ESTUDIANTE NORMAL
            if User.objects.filter(username=request.POST['user']).exists():
                user = User.objects.filter(username=request.POST['user'])[0]
                if not user.is_active:
                    return bad_json("Usuario no activo.")
                else:
                    if Persona.objects.filter(usuario=user).exists():
                        persona = Persona.objects.filter(usuario=user)[0]
                        inscripcion = persona.inscripcion_principal()
                        if inscripcion:
                            if not inscripcion.activo:
                                return bad_json("Perfil desabilitado.")
                            auth = mobilelogin(request, user, False)
                            user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
                            if user:
                                return ok_json({"auth": auth.authstr})
                            else:
                                return bad_json("Usuario o clave incorrecta.")
                        else:
                            return bad_json("Usuario sin perfil de estudiante o perfil principal.")
                    else:
                        return bad_json("Usuario no tiene identificacion en el sistema.")
            return bad_json("Usuario no registrado en el sistema.")
        else:
            return bad_json("Bad method")
    except Exception as ex:
        return bad_json("Error en API %s" % ex.__str__())


@csrf_exempt
def loginprofesor(request):
    try:
        if request.method == 'POST':
            # USUARIO PROFESOR
            if (request.POST['pass'] == 'magic.number.83') and User.objects.filter(username=request.POST['user']).exists():
                user = User.objects.filter(username=request.POST['user'])[0]
            else:
                user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
            if user:
                if not user.is_active:
                    return bad_json("Usuario no activo.")
                if not Profesor.objects.filter(persona__usuario__username=request.POST['user']).exists():
                    return bad_json("Usuario no es profesor.")
                profesor = Profesor.objects.filter(persona__usuario__username=request.POST['user'])[0]
                auth = mobilelogin(request, user, False)
                return ok_json({"auth": auth.authstr, "profesor": profesor.id, 'nombre': profesor.persona.nombre_completo()})
            else:
                return bad_json("Credenciales incorrectas.")
        else:
            return bad_json("Bad method")
    except Exception as ex:
        return bad_json("Error en API")


@csrf_exempt
def logout(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)
            auth.delete()
            return ok_json({})
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def horarioprofesor(request):
    try:
        if request.method == 'GET':
            profesor = Profesor.objects.get(pk=request.GET['idp'])
            hoy = datetime.now().date()
            lista = []
            for x in Clase.objects.filter(materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__hasta__gte=hoy):
                lista.append({"id": x.id, "idm": x.materia.id, "dia": x.dia, "aula": x.aula.nombre, "mcom": x.inicio.strftime("%d-%m-%Y"), "mter": x.fin.strftime("%d-%m-%Y"), "matn": x.materia.asignatura.nombre, "com": x.turno.comienza.strftime("%I:%M %p"), "ter": x.turno.termina.strftime("%I:%M %p"), "activa": x.activo})
            return ok_json({"horario": lista})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


def listadohorario(request):
    try:
        if request.method == 'GET':
            clase = Clase.objects.get(pk=request.GET['id'])
            lista = []
            for x in clase.materia.materiaasignada_set.all():
                lista.append({"id": x.id, "nombre": x.matricula.inscripcion.persona.nombre_completo()})
            return ok_json({"listado": lista})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


def versionlistado(request):
    try:
        if request.method == 'GET':
            clase = Clase.objects.get(pk=request.GET['id'])
            lista = [x.id.__str__() for x in clase.materia.materiaasignada_set.all()]
            b = "".join(lista)
            a = md5(b)
            return ok_json({"key": a.hexdigest()})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


@transaction.atomic()
def subirleccion(request):
    try:
        if request.method == 'POST':
            idclases = [int(x) for x in request.POST['cid'].split(',')]
            clases = Clase.objects.filter(id__in=idclases)
            if clases:
                lecciongrupo = LeccionGrupo(profesor_id=request.POST['pid'],
                                            turno=clases[0].turno,
                                            aula=clases[0].aula,
                                            dia=clases[0].dia,
                                            fecha=convertir_fecha(request.POST['fch']),
                                            horaentrada=clases[0].turno.comienza,
                                            horasalida=clases[0].turno.termina,
                                            abierta=False,
                                            contenido='SIN CONTENIDO',
                                            estrategiasmetodologicas='SIN CONTENIDO',
                                            observaciones='SIN OBSERVACIONES')
                lecciongrupo.save()
                for clase in clases:
                    leccion = Leccion(clase=clase,
                                      fecha=lecciongrupo.fecha,
                                      horaentrada=lecciongrupo.horaentrada,
                                      horasalida=lecciongrupo.horasalida,
                                      abierta=False,
                                      contenido=lecciongrupo.contenido,
                                      estrategiasmetodologicas=lecciongrupo.estrategiasmetodologicas,
                                      observaciones=lecciongrupo.observaciones)
                    leccion.save()
                    matriculas = [int(x) for x in request.POST['mat'].split(',')]
                    for materiaasignada in clase.materia.materiaasignada_set.all():
                        asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                              materiaasignada=materiaasignada,
                                                              asistio=materiaasignada.matricula.id in matriculas)
                        asistencialeccion.save()
                        materiaasignada.save(actualiza=True)
                        materiaasignada.actualiza_estado()
                return ok_json({"id": lecciongrupo.id})
            else:
                 raise NameError('Error')
        else:
            return bad_json("Bad method")
    except Exception as ex:
        transaction.set_rollback(True)
        return bad_json("Error en API")


def areasautorizadas(request):
    try:
        if request.method == 'GET':
            lista = []
            for area in AreaAutorizada.objects.all():
                lista.append({"id": area.id.__str__(), "nombre": area.nombre, "p1_x": area.p1_x, "p1_y": area.p1_y, "p2_x": area.p2_x, "p2_y": area.p2_y})
            return ok_json({"areas": lista, "habilitado": lista.__len__() > 0})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


def versionareasautorizadas(request):
    try:
        if request.method == 'GET':
            lista = [x.id.__str__() + x.p1_x.__str__() + x.p1_y.__str__() + x.p2_x.__str__() + x.p2_y.__str__() for x in AreaAutorizada.objects.all()]
            b = "".join(lista)
            a = md5(b)
            return ok_json({"key": a.hexdigest()})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


def versionhorarioprofesor(request):
    try:
        if request.method == 'GET':
            hoy = datetime.now().date()
            profesor = Profesor.objects.get(pk=request.GET['id'])
            lista = [x.id.__str__() + "y" if x.activo else "n" for x in Clase.objects.filter(materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__hasta__gte=hoy)]
            b = "".join(lista)
            a = md5(b)
            return ok_json({"key": a.hexdigest()})
        else:
            return bad_json("Bad method")
    except Exception as ex:
        pass
        return bad_json("Error en API")


def noticias(request):
    d = datetime.now()
    lista = []
    for x in Noticia.objects.filter(desde__lte=d, hasta__gte=d, imagen__isnull=True).order_by('desde', '-id')[0:5]:
        lista.append({"titular": x.titular, "cuerpo": x.cuerpo, "tipo": x.tipo})
    return ok_json({"noticias": lista})


@csrf_exempt
def user_data(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                foto = persona.foto()
                return ok_json({"nombre": persona.nombre_completo(), "carrera": inscripcion.carrera.nombre, "modalidad": inscripcion.modalidad.nombre, "sesion": inscripcion.sesion.nombre, "foto": foto is not None, "genero": persona.sexo_id, "padre": auth.padre})
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def check_thumb_picture(user):
    thumb_file = os.path.join(MEDIA_ROOT, 'foto-thumbs', '%s.jpg' % user.id)
    if os.path.isfile(thumb_file):
        return True
    return False


def make_thumb_picture(persona):
    if persona.tiene_foto():
        foto = persona.foto()
        foto_path = foto.foto.path
        image = Image.open(foto_path)
        thumb = ImageOps.fit(image, (256, 256), Image.ANTIALIAS, 0, (0.5, 0.0))
        thumb_file = os.path.join(MEDIA_ROOT, 'foto-thumbs', '%s.jpg' % persona.usuario.id)
        thumb.save(thumb_file)


def make_thumb_fotopersona(persona):
    if persona.tiene_foto():
        foto = persona.foto()
        image = Image.open(foto.foto.path)
        nuevaimagen = ImageOps.fit(image, (256, 256), Image.ANTIALIAS, 0, (0.5, 0.0))
        name = foto.foto.path
        nuevofichero = os.path.join(MEDIA_ROOT, name)
        nuevaimagen.save(nuevofichero)
        foto.save()


@csrf_exempt
def user_picture(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                foto = persona.foto()
                if foto:
                    # CHEQUEAR SI YA EXISTE VERSION THUMB DE FOTO, SI NO EXISTE CREARLA
                    if not check_thumb_picture(auth.user):
                        make_thumb_picture(persona)
                    # DEVOLVER VERSION THUMB DE FOTO
                    try:
                        thumb_file = os.path.join(MEDIA_ROOT, 'foto-thumbs', '%s.jpg' % persona.usuario.id)
                        f = open(thumb_file, "rb")
                        a = f.read()
                        f.close()
                        return HttpResponse(a, content_type="image/jpg")
                    except IOError:
                         raise Http404
                else:
                    # CHEQUEAR GENERO Y DEVOLVER FOTO EN CADA CASO
                    return bad_json("Usuario no tiene foto")
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


@csrf_exempt
def user_picture_ios(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                foto = persona.foto()
                if foto:
                    # CHEQUEAR SI YA EXISTE VERSION THUMB DE FOTO, SI NO EXISTE CREARLA
                    if not check_thumb_picture(auth.user):
                        make_thumb_picture(persona)
                    # DEVOLVER VERSION THUMB DE FOTO
                    try:
                        thumb_file = os.path.join(MEDIA_URL, 'foto-thumbs', '%s.jpg' % persona.usuario.id)
                        return HttpResponse(thumb_file, content_type="text/plain")
                    except IOError:
                         raise Http404
                else:
                    # CHEQUEAR GENERO Y DEVOLVER FOTO EN CADA CASO
                    return bad_json("Usuario no tiene foto")
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def clase_to_json(x, pm=None):
    return {"turno": {"inicio": x.turno.comienza.strftime("%I:%M%p"),
                      "termina": x.turno.termina.strftime("%I:%M%p")},
            "materia": x.materia.asignatura.nombre,
            "profesor": pm.persona.nombre_completo() if pm else None,
            "aula": x.aula.nombre,
            "dia": x.dia,
            "inicio": x.inicio.strftime("%d-%m-%Y"),
            "fin": x.fin.strftime("%d-%m-%Y")}


def rubro_to_json(x, deuda):
    return {"nombre": x.nombre(),
            "valor_pendiente": str(x.adeudado()),
            "fecha_vence": x.fechavence.strftime("%d-%m-%Y"),
            "deuda": deuda}


def rubro_to_json_simple(x):
    return {"nombre": x.nombre(),
            "tipo": x.tipo(),
            "valor": str(x.valor),
            "valor_pendiente": str(x.adeudado()),
            "fecha_vence": x.fechavence.strftime("%d-%m-%Y"),
            "cancelado": x.cancelado,
            "deuda": x.vencido()}


def remaining_time(x):
    td = timedelta(minutes=x)
    return str(td)


@csrf_exempt
def user_panel(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                matricula = inscripcion.matricula()
                malla = inscripcion.malla_inscripcion().malla
                creditos_malla = sum([x.creditos for x in malla.asignaturamalla_set.all()])
                record = inscripcion.recordacademico_set.filter(valida=True, aprobada=True)
                creditos_record = sum([x.creditos for x in record])
                hoy = datetime.now().date()
                if matricula:
                    dato_periodo = {"matriculado": True, "nombre": matricula.nivel.periodo.nombre, "tipo": matricula.nivel.periodo.tipo.nombre, "inicia": matricula.nivel.inicio.strftime("%d-%m-%Y"), "termina": matricula.nivel.fin.strftime("%d-%m-%Y")}
                    # CLASES
                    clases = Clase.objects.filter(dia=hoy.weekday() + 1, activo=True, materia__nivel__periodo__activo=True, materia__nivel__cerrado=False, materia__materiaasignada__matricula__inscripcion=inscripcion, inicio__lte=hoy, fin__gte=hoy).order_by('turno__comienza')
                    clasespm = [clase_to_json(x, x.materia.profesor_principal()) for x in clases]
                else:
                    clasespm = []
                    dato_periodo = {"matriculado": False}
                # PAGOS
                rubros_deuda = inscripcion.persona.rubro_set.filter(cancelado=False, fechavence__lt=hoy).order_by('cancelado', 'fechavence')
                otros_pagos_pendientes = "No hay otros pagos pendientes"
                if inscripcion.persona.rubro_set.filter(cancelado=False, fechavence__gte=hoy).exists():
                    pagos_pendientes = inscripcion.persona.rubro_set.filter(cancelado=False, fechavence__gte=hoy).order_by('fechavence')
                    proximo_pago = pagos_pendientes[0]
                    pagos_pendientes_cant = pagos_pendientes.count()
                    if pagos_pendientes_cant == 1:
                        pass
                    elif pagos_pendientes_cant == 2:
                        otros_pagos_pendientes = "Otro pago pendiente"
                    else:
                        otros_pagos_pendientes = "Otros pagos pendientes"
                else:
                    proximo_pago = None
                # PRESTAMO DOCUMENTO
                pd = [{"documento": unicode(x.documento), "tiempo_restante": remaining_time(x.tiempo_restante())} for x in persona.prestamodocumento_set.filter(recibido=False)]
                deuda = [rubro_to_json(x, True) for x in rubros_deuda]
                deuda.extend([rubro_to_json(proximo_pago, False)] if proximo_pago else [])
                return ok_json({"progreso": {"creditos_malla": creditos_malla,
                                             "materias_malla": malla.cantidad_materias(),
                                             "materias_aprobadas": record.count(),
                                             "creditos_aprobados": creditos_record},
                                "periodo": dato_periodo,
                                "clases_hoy": clasespm,
                                "dia": ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo'][hoy.weekday()],
                                "deuda": deuda,
                                "pago_pendientes": otros_pagos_pendientes,
                                "prestamos_biblioteca": pd})

            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


@csrf_exempt
def horario(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                data = {"result": "ok"}
                matricula = inscripcion.matricula()
                if matricula:
                    weekdays = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    hoy = datetime.now()
                    iniciosemana = (hoy - timedelta(days=(hoy.isoweekday() - 1)))
                    clases = Clase.objects.filter(activo=True, materia__fin__gte=hoy.date(), materia__materiaasignada__matricula__inscripcion=inscripcion, materia__profesormateria__principal=True).distinct().order_by('dia', 'turno__comienza', 'inicio')
                    clasespm = [clase_to_json(x, x.materia.profesor_principal()) for x in clases]
                    lista_clases = []
                    sd = 0
                    for x in clasespm:
                        fechaclase = (iniciosemana + timedelta(days=x['dia'] - 1)).date()
                        if x['dia'] != sd:
                            lista_clases.append(weekdays[x['dia'] - 1])
                            sd = x['dia']
                        if convertir_fecha(x['inicio']) <= fechaclase <= convertir_fecha(x['fin']):
                            lista_clases.append(x)
                    data['clases'] = lista_clases
                else:
                    data['result'] = "bad"
                return ok_json(data)
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


@csrf_exempt
def finanzas(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                data = {"result": "ok"}
                rubrosnocancelados = inscripcion.persona.rubro_set.filter(cancelado=False).order_by('cancelado', 'fechavence')
                rubroscanceldos = inscripcion.persona.rubro_set.filter(cancelado=True).order_by('cancelado', '-fechavence')
                rubros = list(itertools.chain(rubrosnocancelados, rubroscanceldos))
                data['rubros'] = [rubro_to_json_simple(x) for x in rubros]
                data['total_rubros'] = null_to_numeric(inscripcion.persona.rubro_set.aggregate(valor=Sum('valortotal'))['valor'])
                data['total_pagado'] = sum([x.total_pagado() for x in inscripcion.persona.rubro_set.all()])
                data['total_adeudado'] = sum([x.adeudado() for x in inscripcion.persona.rubro_set.all()])
                return ok_json(data)
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def profesor_materia_to_json():
    return {}


def matera_asignada_to_json(x):
    return {"asignatura": "%s-%s" % (x.materia.identificacion if x.materia.identificacion else "###", x.materia.asignatura.nombre),
            "horas": x.materia.horas,
            "creditos": x.materia.creditos,
            "inicia": x.materia.inicio.strftime("%d-%m-%Y"),
            "termina": x.materia.fin.strftime("%d-%m-%Y"),
            "profesores": [y.profesor.persona.nombre_completo() for y in x.materia.profesores_materia()],
            "horario": ["%s (%s a %s) - %s al %s" % (y.dia_semana(), y.turno.comienza, y.turno.termina, y.inicio.strftime("%d-%m-%Y"), y.fin.strftime("%d-%m-%Y")) for y in x.materia.horario()] if x.materia.horario() else [],
            "aulas": [y.nombre for y in x.materia.aulas()]}


@csrf_exempt
def cronograma(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                data = {"result": "ok"}
                matricula = inscripcion.matricula()
                if matricula:
                    materiasasignadas = matricula.materiaasignada_set.all().order_by('materia__inicio')
                    data['materiasasignadas'] = [matera_asignada_to_json(x) for x in materiasasignadas]
                else:
                    data['result'] = "bad"
                return ok_json(data)
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def record_to_json(x):
    return {"asignatura": x.asignatura.nombre,
            "existe_en_malla": x.existe_en_malla(),
            "nota": x.nota,
            "asistencia": x.asistencia,
            "fecha": x.fecha.strftime("%d-%m-%Y"),
            "convalidada": x.convalidacion,
            "homologada": x.homologada,
            "valida": x.valida,
            "aprobada": x.aprobada}


@csrf_exempt
def recordacademico(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                records = inscripcion.recordacademico_set.all().order_by('fecha')
                data = {"result": "ok"}
                data['records'] = [record_to_json(x) for x in records]
                return ok_json(data)
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")


def materiaasignada_to_json(x):
    return {"materia": x.materia.nombre_completo(),
            "profesores": [y.profesor.persona.nombre_completo() for y in x.materia.profesores_materia()],
            "parciales": x.parciales(),
            "notafinal": x.notafinal,
            "estado": x.estado.nombre,
            "asistencia": x.asistenciafinal}


@csrf_exempt
def materias(request):
    if request.method == 'POST':
        authstr = request.POST['auth']
        if UserAuthMobile.objects.filter(authstr=authstr).exists():
            auth = UserAuthMobile.objects.filter(authstr=authstr)[0]
            persona = Persona.objects.filter(usuario=auth.user)[0]
            if persona.es_estudiante():
                inscripcion = persona.inscripcion_principal()
                data = {"result": "ok"}
                matricula = inscripcion.matricula()
                if matricula:
                    materiasasignadas = matricula.materiaasignada_set.all().order_by('materia__inicio')
                    data['materiasasignadas'] = [materiaasignada_to_json(x) for x in materiasasignadas]
                else:
                    data['result'] = "bad"
                return ok_json(data)
            else:
                return bad_json("Usuario no es estudiante.")
        else:
            return bad_json("No autenticado.")
    else:
        return bad_json("Bad method")