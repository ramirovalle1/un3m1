# coding=utf-8
from __future__ import division

import re
import sys
from datetime import timedelta, date, time
from operator import itemgetter
import os
import json
import io as StringIO

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection, connections
from django.contrib.admin.models import LogEntry, ADDITION, DELETION, CHANGE
from django.contrib.auth.models import User, Group, _user_has_perm
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.http import HttpResponse
# from ho import pisa
# from redis.commands.search.reducers import max
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.formatters import DecimalFormatter
from xhtml2pdf import pisa
from django.db.models import Func, Q, Avg, F,Count
from settings import DIAS_MATRICULA_EXPIRA, CLAVE_USUARIO_CEDULA, DEFAULT_PASSWORD, MEDIA_ROOT, MEDIA_URL, \
    AUDITAR_USUARIO, CORREO_AUDITOR, ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, ADMINISTRADOR_ID

import unicodedata
import socket


from sga.tasks import send_html_mail
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


unicode = str


class MiPaginador(Paginator):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, rango=5):
        super(MiPaginador, self).__init__(object_list, per_page, orphans=orphans, allow_empty_first_page=allow_empty_first_page)
        self.rango = rango
        self.paginas = []
        self.primera_pagina = False
        self.ultima_pagina = False

    def rangos_paginado(self, pagina):
        left = pagina - self.rango
        right = pagina + self.rango
        if left < 1:
            left = 1
        if right > self.num_pages:
            right = self.num_pages
        self.paginas = range(left, right + 1)
        self.primera_pagina = True if left > 1 else False
        self.ultima_pagina = True if right < self.num_pages else False
        self.ellipsis_izquierda = left - 1
        self.ellipsis_derecha = right + 1


def proximafecha(fecha, periocidad, dia=None):
    if periocidad == 1:
        # DIARIO
        return fecha + timedelta(days=1)
    if periocidad == 2:
        # SEMANAL
        return fecha + timedelta(days=7)
    if periocidad == 3:
        # MENSUAL
        if dia:
            day = dia
        else:
            day = fecha.day
        month = fecha.month
        year = fecha.year
        if month == 12:
            nextmonth = 1
            nextyear = year + 1
        else:
            nextmonth = month + 1
            nextyear = year
        # if day >= 29:
        #     for i in range(29, 32):
        #         nuevafecha = fecha + timedelta(days=i)
        #         if nuevafecha.month == nextmonth:
        #             return nuevafecha
        # else:
        fechafinal = datetime.now().date()
        try:
            fechafinal = datetime(nextyear, nextmonth, day)
        except:
            try:
                day -= 1
                fechafinal = datetime(nextyear, nextmonth, day)
            except:
                try:
                    day -= 1
                    fechafinal = datetime(nextyear, nextmonth, day)
                except:
                    try:
                        day -= 1
                        fechafinal = datetime(nextyear, nextmonth, day)
                    except:
                        pass
        return fechafinal


def generar_usuario_cedula(persona, usuario, group_id):
    password = persona.identificacion().strip()
    emailinst_ = '{}@unemi.edu.ec'.format(usuario)
    user = User.objects.create_user(usuario, emailinst_, password)
    # user.emailinst = emailinst_
    # user.save()
    persona.usuario = user
    # persona.email = user.emailinst
    persona.save()
    persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()


def generar_usuario(persona, usuario, group_id):
    password = DEFAULT_PASSWORD
    anio = ''
    if persona.nacimiento:
        anio = "*" + str(persona.nacimiento)[0:4]
    if CLAVE_USUARIO_CEDULA:
        password = persona.cedula.strip() + anio
    try:
        emailinst_ = '{}@unemi.edu.ec'.format(usuario)
        user = User.objects.create_user(usuario, emailinst_, password)
    except Exception as ex:
        raise NameError(f'La persona con usuario "{usuario}" ya se encuentra registrada.')
    user.emailinst = '{}@unemi.edu.ec'.format(usuario)
    user.save()
    persona.usuario = user
    # persona.email = user.emailinst
    persona.save()
    persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()


def generar_usuario_admision(persona, usuario, group_id):
    password = persona.identificacion()
    mail = persona.email
    emailinst_ = '{}@unemi.edu.ec'.format(usuario)
    user = User.objects.create_user(usuario.strip(), emailinst_, password)
    user.last_name = "%s %s" % (persona.apellido1, persona.apellido2)
    user.first_name = persona.nombres
    user.emailinst = emailinst_
    user.save()
    persona.usuario = user
    persona.emailinst = user.emailinst
    persona.save()
    # persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()

def generar_usuario_formacion(persona, usuario):
    password = persona.identificacion()
    mail = persona.email
    user = User.objects.create_user(usuario.strip(), mail, password)
    user.last_name = "%s %s" % (persona.apellido1, persona.apellido2)
    user.first_name = persona.nombres
    user.save()
    persona.usuario = user
    persona.emailinst = user.emailinst
    persona.save()


def generar_usuario_sin_perfil(persona, usuario):
    from sga.models import Externo
    from moodle.models import UserAuth
    password = persona.identificacion()
    emailinst_ = '{}@unemi.edu.ec'.format(usuario)
    user = User.objects.create_user(usuario, emailinst_, password)
    user.save()
    persona.usuario = user
    persona.save()
    if not Externo.objects.filter(status=True, persona=persona).exists():
        externo = Externo(persona=persona,
                          nombrecomercial='',
                          nombrecontacto='',
                          telefonocontacto='')
        externo.save()
    else:
        externo = Externo.objects.get(status=True, persona=persona)
    persona.crear_perfil(externo=externo)
    persona.clave_cambiada()
    if not UserAuth.objects.filter(usuario=usuario).exists():
        usermoodle = UserAuth(usuario=usuario)
        usermoodle.set_data()
        usermoodle.set_password(password)
        usermoodle.save()
    else:
        usermoodle=UserAuth.objects.filter(usuario=usuario).first()
        usermoodle.set_data()
        usermoodle.save()

def generar_usuario_externo(persona, usuario, group_id):
    password = DEFAULT_PASSWORD
    anio = ''
    if persona.nacimiento:
        anio = "*" + str(persona.nacimiento)[0:4]
    if CLAVE_USUARIO_CEDULA:
        password = persona.cedula.strip() + anio
    emailinst_ = '{}@unemi.edu.ec'.format(usuario)

    #Creamos el usuario
    user = User.objects.create_user(usuario, emailinst_, password)
    persona.usuario = user
    persona.save()

    #Habilitmos el cambio de clave
    persona.cambiar_clave()

    #Agregamos al grupo que pertenece
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()
    return password

def resetear_clavepostulante(persona):
    if not persona.usuario.is_superuser and not persona.es_administrativo() \
            and not persona.es_estudiante() and not persona.es_profesor():
        if persona.cedula:
            password = persona.cedula.strip()
        elif persona.pasaporte:
            password = persona.pasaporte.strip()
        user = persona.usuario
        user.set_password(password)
        user.save()
        if variable_valor('VALIDAR_LDAP'):
            validar_ldap(user.username, password, persona)


def resetear_clave(persona):
    from sga.models import UsuarioLdap
    password = DEFAULT_PASSWORD
    anio = ''
    if persona.nacimiento:
        anio = "*" + str(persona.nacimiento)[0:4]
    if CLAVE_USUARIO_CEDULA:
        if not persona.usuario.is_superuser:
            if persona.cedula:
                password = persona.cedula.strip() + anio
            elif persona.pasaporte:
                password = persona.pasaporte.strip() + anio
            else:
                password = persona.ruc.strip() + anio
            user = persona.usuario
            user.set_password(password)
            user.save()
            UsuarioLdap.objects.filter(usuario=user).delete()
            persona.cambiar_clave()
            if variable_valor('VALIDAR_LDAP'):
                validar_ldap(user.username, password, persona)


def resetear_clave_postulate(persona):
    from sga.models import UsuarioLdap
    password = DEFAULT_PASSWORD
    anio = ''
    if persona.nacimiento:
        anio = "*" + str(persona.nacimiento)[0:4]
    if CLAVE_USUARIO_CEDULA:
        if not persona.usuario.is_superuser:
            if persona.cedula:
                password = persona.cedula.strip() + anio
            elif persona.pasaporte:
                password = persona.pasaporte.strip() + anio
            else:
                password = persona.ruc.strip() + anio
            user = persona.usuario
            user.set_password(password)
            user.save()
            UsuarioLdap.objects.filter(usuario=user).delete()
            persona.cambiar_clave()


def resetear_clave_admision_manual(persona):
    cursor = connections['db_moodle_virtual'].cursor()
    password = persona.identificacion()
    if not persona.usuario.is_superuser:
        if persona.inscripcion_set.filter(status=True).exists():
            user = persona.usuario
            user.set_password(password)
            user.save()
            persona.cambiar_clave()
            sql = """
            UPDATE mooc_user 
            SET password = MD5('%s')
            WHERE username='%s'
            """ % (password, user)
            cursor.execute(sql)


def resetear_clave_admision_ldap(persona):
    password = DEFAULT_PASSWORD
    if not persona.usuario.is_superuser:
        if persona.cedula:
            password = persona.cedula.strip()
        elif persona.pasaporte:
            password = persona.pasaporte.strip()
        else:
            password = persona.ruc.strip()
        user = persona.usuario
        user.set_password(password)
        user.save()
        persona.cambiar_clave()
        if variable_valor('VALIDAR_LDAP'):
            try:
                validar_ldap(user.username, password, persona)
            except Exception as ex:
                pass


def resetear_clave_pregrado_virtual(persona):
    password = persona.identificacion()
    if not persona.usuario.is_superuser:
        if persona.inscripcion_set.filter(status=True, carrera__modalidad=3).exists():
            user = persona.usuario
            user.set_password(password)
            user.save()
            persona.cambiar_clave()
            if variable_valor('VALIDAR_LDAP'):
                validar_ldap_reseteo(user.username, password, persona)


def resetear_clave_empresa(persona):
    password = DEFAULT_PASSWORD
    user = persona.usuario
    user.set_password(password)
    user.is_active = True
    user.save()
    persona.cambiar_clave()
    if not persona.tiene_perfil():
        persona.crear_perfil(empleador=persona.empleador_set.all()[0])


def remover_caracteres_especiales_unicode(cadena):
    return cadena.replace(u'ñ', u'n').replace(u'Ñ', u'N').replace(u'Á', u'A').replace(u'á', u'a').replace(u'É', u'E').replace(u'é', u'e').replace(u'Í', u'I').replace(u'í', u'i').replace(u'Ó', u'O').replace(u'ó', u'o').replace(u'Ú', u'U').replace(u'ú', u'u')


def remover_comilla_simple(cadena):
    return cadena.replace(u"'", u'')


def remover_caracteres_tildes_unicode(cadena):
    return cadena.replace(u'Á', u'A').replace(u'á', u'a').replace(u'É', u'E').replace(u'é', u'e').replace(u'Í',
                                                                                                          u'I').replace(
        u'í', u'i').replace(u'Ó', u'O').replace(u'ó', u'o').replace(u'Ú', u'U').replace(u'ú', u'u')


def elimina_tildes(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD', unicode(cadena)) if unicodedata.category(c) != 'Mn'))
    # return s.decode()
    return s


def remover_caracteres(texto, caracteres_a_remover):
    string = ''.join(c for c in texto if c not in caracteres_a_remover)
    return string


def remover_atributo_style_html(html):
    style = re.compile(' style\=.*?\".*?\"')
    html = re.sub(style, '', html)
    return html


def isInsideUnemi(latitude, longitude):
    from shapely.geometry import Polygon, Point

    unemi_coordinates = [
        (-2.148605, -79.603839),
        (-2.148007, -79.602527),
        (-2.148791, -79.601321),
        (-2.150340, -79.601908),
        (-2.152234, -79.602558),
        (-2.151770, -79.603521),
        (-2.152124, -79.603730),
        (-2.151205, -79.605630),
        (-2.149853, -79.604261),
        (-2.149051, -79.604053),
        (-2.148605, -79.603839)
    ]

    unemi_poly = Polygon(unemi_coordinates)
    user_current_location = Point(latitude, longitude)

    return unemi_poly.contains(user_current_location)



def calculate_username(persona, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = persona.nombres.lower().split(' ')
    while '' in s:
        s.remove('')
    if persona.apellido2:
        usernamevariant = s[0][0] + persona.apellido1.lower() + persona.apellido2.lower()[0]
    else:
        usernamevariant = s[0][0] + persona.apellido1.lower()
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(
        u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)

    if not User.objects.filter(username=usernamevariantfinal).exclude(persona=persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username(persona, variant + 1)


def logproceso(mensaje, accion, user=None):
    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE

    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=None,
        object_id=None,
        object_repr='',
        action_flag=logaction,
        change_message=unicode(mensaje))


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log(mensaje, request, accion, user=None):

    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE
    #if not user:
    #    if request.user.username in AUDITAR_USUARIO:
    #        send_html_mail("Auditor SGA.", "emails/auditoria.html",
    #                       {'sistema': u'Auditoria de Sistema', 'fecha': datetime.now().date(),
    #                        'usuario': request.user.username.upper(), 'hora': datetime.now().time(),
    #                        'mensaje': unicode(mensaje)}, CORREO_AUDITOR, [])
    if variable_valor('GUARDA_LOG_BD'):
        if request:
            from user_agents import parse
            user_agent = parse(request.META.get('HTTP_USER_AGENT'))
            user_ip = get_client_ip(request)
            user_device = user_agent.device.family
            user_browser = user_agent.browser.family
            user_os_type = user_agent.os.family
            user_os_version = user_agent.os.version_string
            user_device_type = 'Otros'
            if user_agent.is_pc:
                user_device_type = 'PC'
            elif user_agent.is_mobile:
                user_device_type = 'Telófono Movil'
            elif user_agent.is_tablet:
                user_device_type = 'Tablet'
            mensaje = f'{mensaje}    --IP: {user_ip}   --Dispositivo: {user_device_type}/{user_device}   --Navegador/OS: {user_browser}/{user_os_type}-{user_os_version}'
        LogEntry.objects.log_action(
            user_id=request.user.id if not user else user.id,
            content_type_id=None,
            object_id=None,
            object_repr='',
            action_flag=logaction,
            change_message=unicode(mensaje))

def logobjeto(mensaje, request, accion, user=None,objeto=None):
    contenido = None
    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE
    if objeto:
        aplicacion = objeto._meta.app_label
        modelo = objeto._meta.model_name
        contenido = ContentType.objects.filter(app_label=aplicacion,model=modelo).first()

    if variable_valor('GUARDA_LOG_BD'):
        if request:
            from user_agents import parse
            user_agent = parse(request.META.get('HTTP_USER_AGENT'))
            user_ip = get_client_ip(request)
            user_device = user_agent.device.family
            user_browser = user_agent.browser.family
            user_os_type = user_agent.os.family
            user_os_version = user_agent.os.version_string
            user_device_type = 'Otros'
            if user_agent.is_pc:
                user_device_type = 'PC'
            elif user_agent.is_mobile:
                user_device_type = 'Telófono Movil'
            elif user_agent.is_tablet:
                user_device_type = 'Tablet'
            mensaje = f'{mensaje}    --IP: {user_ip}   --Dispositivo: {user_device_type}/{user_device}   --Navegador/OS: {user_browser}/{user_os_type}-{user_os_version}'
        LogEntry.objects.log_action(
            user_id=request.user.id if not user else user.id,
            content_type_id=contenido.id if contenido else None,
            object_id= objeto.id if objeto else None,
            object_repr=objeto.__str__() if objeto else '',
            action_flag=logaction,
            change_message=unicode(mensaje))


def loglogin(action_flag, action_app, ip_private, ip_public, browser, ops, cookies, screen_size, user=None, change_message=None):
    from bd.models import LogEntryLogin
    LogEntryLogin.objects.log_action(user=user,
                                     action_flag=action_flag,
                                     action_app=action_app,
                                     ip_private=ip_private,
                                     ip_public=ip_public,
                                     browser=browser,
                                     ops=ops,
                                     cookies=cookies,
                                     screen_size=screen_size,
                                     change_message=change_message)


def logquery(baseafectada, query, filasafectadas, request, url=None):
    from bd.models import LogQuery
    if not url:
        if not LogQuery.objects.filter(baseafectada=baseafectada, query=query, filasafectadas=filasafectadas, fecha_creacion__date=str(date.today())).exists():
            log = LogQuery(baseafectada=baseafectada, query=query, filasafectadas=filasafectadas)
            log.save(request)
    else:
        log = LogQuery(baseafectada=baseafectada, query=query, filasafectadas=filasafectadas, url_archivo=url)
        log.save(request)


def salvaRubros(request, model, action, qs_nuevo=None, qs_anterior=None):
    from sagest.models import logRubros
    import json
    arr = []
    anterior = {}
    nuevo = {}
    if qs_anterior:
        anterior["fields"] = {}
        for x in qs_anterior:
            for k, v in x.items():
                anterior["fields"][k] = str(v)
        anterior["pk"] = qs_anterior[0]["id"]
        anterior["fields"]["__ff_detalle_ff__"] = "ANTERIOR"
        anterior["model"] = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        arr.append(anterior)
    if qs_nuevo:
        nuevo["fields"] = {}
        for x in qs_nuevo:
            for k, v in x.items():
                nuevo["fields"][k] = str(v)
        nuevo["pk"] = qs_nuevo[0]["id"]
        nuevo["fields"]["__ff_detalle_ff__"] = "NUEVO"
        nuevo["model"] = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        arr.append(nuevo)
    data_json = json.dumps(arr)
    userid = request.user.pk
    auditusuariotabla = logRubros(usuario_id=userid,
                                  idrubro=model.id,
                                  rubroname=model.nombre,
                                  cedulapersona=model.persona.cedula,
                                  persona=model.persona.__str__(),
                                  accion=action.upper(),
                                  datos_json=data_json)
    auditusuariotabla.save(request)


def convertir_fecha(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'

    return date(int(s.split(sep)[2]), int(s.split(sep)[1]), int(s.split(sep)[0]))


def convertir_hora(s):
    if ':' in s:
        sep = ':'
    return time(int(s.split(sep)[0]), int(s.split(sep)[1]))


def convertir_hora_completa(s):
    if ':' in s:
        sep = ':'
    return time(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]))


def convertir_fecha_invertida(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return date(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]))


def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha


def formato24h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    meridiano = hora.partition(":")[2].partition(" ")[2]
    if meridiano == "AM":
        if horas == "12":
            return "00" + ":" + minutos + ":00"
        else:
            return horas + ":" + minutos + ":00"
    else:
        if horas == "12":
            return horas + ":" + minutos + ":00"
        else:
            return str(int(horas) + 12) + ":" + minutos + ":00"


def formato12h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    if horas >= "12":
        if horas == "12":
            return horas + ":" + minutos + " PM"
        else:
            return str(int(horas) - 12) + ":" + minutos + " PM"
    else:
        if horas == "0":
            return "12:" + minutos + " AM"
        else:
            return horas + ":" + minutos + " AM"


def remover_caracteres_especiales(cadena):
    s = ''.join((c if c != ' ' else '_' for c in unicodedata.normalize('NFD', cadena) if unicodedata.category(c) != 'Mn'))
    # return s.decode()
    return s


def to_unicode(s):
    if isinstance(s, unicode):
        return s

    from locale import getpreferredencoding

    for cp in (getpreferredencoding(), "cp1255", "cp1250"):
        try:
            return unicode(s, cp)
        except UnicodeDecodeError:
            pass
        raise Exception("Conversion to unicode failed")


def generar_nombre(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    fecha = datetime.now().date()
    hora = datetime.now().time()
    nombre = remover_caracteres_especiales(nombre)
    return nombre + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + ext.lower()


def generar_nombre_video(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    name = original.split('.')[0]
    # fecha = datetime.now().date()
    return nombre + name + ext.lower()


def tituloinstitucion():
    from sga.models import TituloInstitucion
    if TituloInstitucion.objects.all().exists():
        tituloinst = TituloInstitucion.objects.all()[0]
    else:
        tituloinst = TituloInstitucion(nombre="Sistema academico",
                                       direccion="",
                                       telefono="",
                                       correo="",
                                       web="",
                                       municipio="")
        tituloinst.save()
    return tituloinst


def obtener_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

#FUNCION VALIDA ERRONEAMENTE VARIAS CÉDULAS
# def validarcedula(numero):
#     suma = 0
#     residuo = 0
#     pri = False
#     pub = False
#     nat = False
#     numeroprovincias = 24
#     modulo = 11
#     if numero.__len__() != 10:
#         return 'El número de cédula no es válido, debe tener 10 dígitos'
#     prov = numero[0:2]
#     if int(prov) > numeroprovincias or int(prov) <= 0:
#         return 'El código de la provincia (dos primeros dígitos) es inválido'
#     d1 = numero[0:1]
#     d2 = numero[1:2]
#     d3 = numero[2:3]
#     d4 = numero[3:4]
#     d5 = numero[4:5]
#     d6 = numero[5:6]
#     d7 = numero[6:7]
#     d8 = numero[7:8]
#     d9 = numero[8:9]
#     d10 = numero[9:10]
#     p1 = 0
#     p2 = 0
#     p3 = 0
#     p4 = 0
#     p5 = 0
#     p6 = 0
#     p7 = 0
#     p8 = 0
#     p9 = 0
#     if int(d3) == 7 or int(d3) == 8:
#         return 'El tercer dígito ingresado es inválido'
#     if int(d3) < 6:
#         nat = True
#         p1 = int(d1) * 2
#         if p1 >= 10:
#             p1 -= 9
#         p2 = int(d2) * 1
#         if p2 >= 10:
#             p2 -= 9
#         p3 = int(d3) * 2
#         if p3 >= 10:
#             p3 -= 9
#         p4 = int(d4) * 1
#         if p4 >= 10:
#             p4 -= 9
#         p5 = int(d5) * 2
#         if p5 >= 10:
#             p5 -= 9
#         p6 = int(d6) * 1
#         if p6 >= 10:
#             p6 -= 9
#         p7 = int(d7) * 2
#         if p7 >= 10:
#             p7 -= 9
#         p8 = int(d8) * 1
#         if p8 >= 10:
#             p8 -= 9
#         p9 = int(d9) * 2
#         if p9 >= 10:
#             p9 -= 9
#         modulo = 10
#     elif int(d3) == 6:
#         pub = True
#         p1 = int(d1) * 3
#         p2 = int(d2) * 2
#         p3 = int(d3) * 7
#         p4 = int(d4) * 6
#         p5 = int(d5) * 5
#         p6 = int(d6) * 4
#         p7 = int(d7) * 3
#         p8 = int(d8) * 2
#         p9 = 0
#     elif int(d3) == 9:
#         pri = True
#         p1 = int(d1) * 4
#         p2 = int(d2) * 3
#         p3 = int(d3) * 2
#         p4 = int(d4) * 7
#         p5 = int(d5) * 6
#         p6 = int(d6) * 5
#         p7 = int(d7) * 4
#         p8 = int(d8) * 3
#         p9 = int(d9) * 2
#     suma = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
#     residuo = suma % modulo
#     if residuo == 0:
#         digitoverificador = 0
#     else:
#         digitoverificador = modulo - residuo
#     if nat:
#         if digitoverificador != int(d10):
#             return 'El número de cédula de la persona natural es incorrecto'
#         else:
#             return 'Ok'
#     else:
#         return 'El número de cédula introducido es incorrecto'
#VALIDAR IDENTIFICACIÓN CÉDULA Y RUC
# def validarcedula(nro, tipo=0):
#     nro = nro.replace("-", "").replace(" ", "")
#     if not nro.isdigit():
#         return "Por favor digitar solo números"
#     total = 0
#     if tipo == 0:  # cedula y r.u.c persona natural
#         base = 10
#         d_ver = int(nro[9])  # digito verificador
#         multip = (2, 1, 2, 1, 2, 1, 2, 1, 2)
#     elif tipo == 1:  # r.u.c. publicos
#         base = 11
#         d_ver = int(nro[8])
#         multip = (3, 2, 7, 6, 5, 4, 3, 2)
#     elif tipo == 2:  # r.u.c. juridicos y extranjeros sin cedula
#         base = 11
#         d_ver = int(nro[9])
#         multip = (4, 3, 2, 7, 6, 5, 4, 3, 2)
#     if len(nro) < base:
#         return f"Identificación ingresada tiene menos de {base} números"
#     for i in range(0, len(multip)):
#         p = int(nro[i]) * multip[i]
#         if tipo == 0:
#             total += p if p < 10 else int(str(p)[0]) + int(str(p)[1])
#         else:
#             total += p
#     mod = total % base
#     val = base - mod if mod != 0 else 0
#     if val!=d_ver:
#         return 'Número de identificación ingresada es incorrecta.'
#     return 'Ok'
def validarcedula(cedula):
    # Eliminar posibles caracteres no numéricos
    cedula = cedula.replace("-", "").replace(" ", "")

    # Verificar si la cédula tiene la longitud correcta
    if len(cedula) != 10:
        return "Cédula ingresada tiene menos de 10 números"

    # Verificar si todos los caracteres son dígitos
    if not cedula.isdigit():
        return "Por favor digitar solo números"

    # Verificar el dígito de verificación
    provincia = int(cedula[0:2])
    if provincia==30:
        # if not cedula.startswith('3050'):
        #     return 'Identificación incorrecta'
        #     # Obtiene los dígitos de la cédula
        # digitos = [int(d) for d in cedula]
        # # Obtiene el dígito verificador
        # verificador = digitos[9]
        # # Calcula la suma ponderada de los dígitos
        # suma_ponderada = sum(digitos[i] * (2 ** (9 - i)) for i in range(9))
        # # Calcula el dígito verificador esperado
        # verificador_esperado = (10 - (suma_ponderada % 10)) % 10
        # # Comprueba si el dígito verificador coincide
        # valido=verificador == verificador_esperado
        return 'Ok'
    else:
        if provincia < 1 or provincia > 24:
            return "Primero dos dígitos incorrecto"

        tercer_digito = int(cedula[2])
        if tercer_digito < 0 or tercer_digito > 6:
            return "Tercer digito fuera de rango"

        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        verificador = int(cedula[9])

        # Calcular el dígito de verificación esperado
        suma = 0
        for i in range(9):
            digito = int(cedula[i])
            producto = digito * coeficientes[i]
            if producto >= 10:
                producto -= 9
            suma += producto

        digito_verificador_esperado = 0
        if suma % 10 != 0:
            digito_verificador_esperado = 10 - (suma % 10)

        # Comparar el dígito de verificación ingresado con el esperado
        if verificador != digito_verificador_esperado:
            return "Cédula incorrecta"

        # Si todas las verificaciones pasaron, la cédula es válida
        return "Ok"

def puede_modificar_inscripcion(request, inscripcion):
    from sga.models import PerfilAccesoUsuario
    for grupo in request.user.groups.all():
        if PerfilAccesoUsuario.objects.values_list('id', flat=True).filter(grupo=grupo, carrera=inscripcion.carrera).exists():
            return True
    raise Exception('Permiso denegado.')


def puede_acceder_modulo(request):
    from sga.models import Modulo
    if request.user.is_authenticated:
        try:
            p = request.session['perfilprincipal']
            app = request.session['tiposistema']
            if len(request.path[1:]) > 1:
                if p.es_estudiante():
                    g = [ALUMNOS_GROUP_ID]
                elif p.es_profesor():
                    g = [PROFESORES_GROUP_ID]
                else:
                    g = [x.id for x in p.persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])]
                if Modulo.objects.filter(modulogrupo__grupos__id__in=g, url=request.path[1:], activo=True).exists():
                    modulo = Modulo.objects.filter(modulogrupo__grupos__id__in=g, url=request.path[1:], activo=True)[0]
                    return True
                else:
                    return False
            else:
                return True
        except Exception as ex:
            return False
    else:
        return False


def puede_modificar_profesor(request, profesor):
    from sga.models import PerfilAccesoUsuario
    for grupo in request.user.groups.all():
        if PerfilAccesoUsuario.objects.filter(grupo=grupo, coordinacion=profesor.coordinacion).exists():
            return True
    raise Exception('Permiso denegado.')


def puede_realizar_accion(request, permiso):
    if request.user.has_perm(permiso):
        return True
    raise Exception('Permiso denegado.')

def puede_realizar_accion2(request, permiso):
    return request.user.has_perm(permiso)

def puede_realizar_accion_is_superuser(request, permiso):
    # Active superusers have all permissions.
    if _user_has_perm(request.user, permiso, None):
        return True
    raise Exception('Permiso denegado.')


def puede_ver_todoadmision(request, permiso):
    if request.user.has_perm(permiso):
        return True
    else:
        return False


def puede_realizar_accion_afirmativo(request, permiso):
    return request.user.has_perm(permiso)


def puede_realizar_acciones_afirmativo(request, permiso_list):
    if request.user.has_perms(permiso_list):
        return True
    return False


def lista_correo(listagrupos):
    from sga.models import Persona
    lista = []
    for persona in Persona.objects.filter(usuario__groups__id__in=listagrupos).distinct():
        lista.extend(persona.lista_emails_envio())
    return lista


def fetch_resources(uri, rel):
    return os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ""))


def generar_pdf(html):
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("UTF-8")),
                            dest=result,
                            link_callback=fetch_resources)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        result.close()
        pisa.log.removeHandler(pisa.log.handlers)
        return response
    return HttpResponse('Tenemos algunos errores<pre>%s</pre>' % html)


(MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)


def addworkdays(start, days, holidays=(), workdays=(MON, TUE, WED, THU, FRI)):
    weeks, days = divmod(days, len(workdays))
    result = start + timedelta(weeks=weeks)
    lo, hi = min(start, result), max(start, result)
    count = len([h for h in holidays if lo <= h <= hi])
    days += count * (-1 if days < 0 else 1)
    for _ in range(days):
        result += timedelta(days=1)
        while result in holidays or result.weekday() not in workdays:
            result += timedelta(days=1)
    return result


def bad_json(mensaje=None, error=None, extradata=None):
    data = {'result': 'bad'}
    if mensaje:
        data.update({'mensaje': mensaje})
    if error:
        if error == 0:
            data.update({"mensaje": "Solicitud incorrecta."})
        elif error == 1:
            data.update({"mensaje": "Error al guardar los datos."})
        elif error == 2:
            data.update({"mensaje": "Error al eliminar los datos."})
        elif error == 3:
            data.update({"mensaje": "Error al obtener los datos."})
        elif error == 4:
            data.update({"mensaje": "No tiene permisos para realizar esta acción."})
        elif error == 5:
            data.update({"mensaje": "Error al generar la información."})
        else:
            data.update({"mensaje": "Error en el sistema."})
    if extradata:
        data.update(extradata)
    return HttpResponse(json.dumps(data), content_type="application/json")


def ok_json(data=None, simple=None):
    if data:
        if not simple:
            if 'result' not in data.keys():
                data.update({"result": "ok"})
    else:
        data = {"result": "ok"}
    return HttpResponse(json.dumps(data), content_type="application/json")


def fechaletra_corta(fecha):
    fechafinal = ''
    if fecha.day == 1:
        fechafinal += 'al primer día '
    if fecha.day == 2:
        fechafinal += 'a los dos días '
    if fecha.day == 3:
        fechafinal += 'a los tres días '
    if fecha.day == 4:
        fechafinal += 'a los cuatro días '
    if fecha.day == 5:
        fechafinal += 'a los cinco días '
    if fecha.day == 6:
        fechafinal += 'a los seis días '
    if fecha.day == 7:
        fechafinal += 'a los siete días '
    if fecha.day == 8:
        fechafinal += 'a los ocho días '
    if fecha.day == 9:
        fechafinal += 'a los nueve días '
    if fecha.day == 10:
        fechafinal += 'a los diez días '
    if fecha.day == 11:
        fechafinal += 'a los once días '
    if fecha.day == 12:
        fechafinal += 'a los doce días '
    if fecha.day == 13:
        fechafinal += 'a los trece días '
    if fecha.day == 14:
        fechafinal += 'a los catorce días '
    if fecha.day == 15:
        fechafinal += 'a los quince días '
    if fecha.day == 16:
        fechafinal += 'a los dieciseis días '
    if fecha.day == 17:
        fechafinal += 'a los diecisiete días '
    if fecha.day == 18:
        fechafinal += 'a los dieciocho días '
    if fecha.day == 19:
        fechafinal += 'a los diecinueve días '
    if fecha.day == 20:
        fechafinal += 'a los veinte días '
    if fecha.day == 21:
        fechafinal += 'a los veintiun días '
    if fecha.day == 22:
        fechafinal += 'a los veintidos días '
    if fecha.day == 23:
        fechafinal += 'a los veintitres días '
    if fecha.day == 24:
        fechafinal += 'a los veinticuatro días '
    if fecha.day == 25:
        fechafinal += 'a los veinticinco días '
    if fecha.day == 26:
        fechafinal += 'a los veintiseis días '
    if fecha.day == 27:
        fechafinal += 'a los veintisiete días '
    if fecha.day == 28:
        fechafinal += 'a los veintiocho días '
    if fecha.day == 29:
        fechafinal += 'a los veintinueve días '
    if fecha.day == 30:
        fechafinal += 'a los treinta días '
    if fecha.day == 31:
        fechafinal += 'a los treinta y un días '
    if fecha.month == 1:
        fechafinal += 'del mes de Enero del '
    if fecha.month == 2:
        fechafinal += 'del mes de Febrero del '
    if fecha.month == 3:
        fechafinal += 'del mes de Marzo del '
    if fecha.month == 4:
        fechafinal += 'del mes de Abril del '
    if fecha.month == 5:
        fechafinal += 'del mes de Mayo del '
    if fecha.month == 6:
        fechafinal += 'del mes de Junio del '
    if fecha.month == 7:
        fechafinal += 'del mes de Julio del '
    if fecha.month == 8:
        fechafinal += 'del mes de Agosto del '
    if fecha.month == 9:
        fechafinal += 'del mes de Septiembre del '
    if fecha.month == 10:
        fechafinal += 'del mes de Octubre del '
    if fecha.month == 11:
        fechafinal += 'del mes de Noviembre del '
    if fecha.month == 12:
        fechafinal += 'del mes de Diciembre del '
    if fecha.year == 1998:
        fechafinal += 'mil novecientos noventa y ocho'
    if fecha.year == 1999:
        fechafinal += 'mil novecientos noventa y nueve'
    if fecha.year == 2000:
        fechafinal += 'dos mil'
    if fecha.year == 2001:
        fechafinal += 'dos mil uno'
    if fecha.year == 2002:
        fechafinal += 'dos mil dos'
    if fecha.year == 2003:
        fechafinal += 'dos mil tres'
    if fecha.year == 2004:
        fechafinal += 'dos mil cuatro'
    if fecha.year == 2005:
        fechafinal += 'dos mil cinco'
    if fecha.year == 2006:
        fechafinal += 'dos mil seis'
    if fecha.year == 2007:
        fechafinal += 'dos mil siete'
    if fecha.year == 2008:
        fechafinal += 'dos mil ocho'
    if fecha.year == 2009:
        fechafinal += 'dos mil nueve'
    if fecha.year == 2010:
        fechafinal += 'dos mil diez'
    if fecha.year == 2011:
        fechafinal += 'dos mil once'
    if fecha.year == 2012:
        fechafinal += 'dos mil doce'
    if fecha.year == 2013:
        fechafinal += 'dos mil trece'
    if fecha.year == 2014:
        fechafinal += 'dos mil catorce'
    if fecha.year == 2015:
        fechafinal += 'dos mil quince'
    if fecha.year == 2016:
        fechafinal += 'dos mil dieciseis'
    if fecha.year == 2017:
        fechafinal += 'dos mil diecisiete'
    if fecha.year == 2018:
        fechafinal += 'dos mil dieciocho'
    if fecha.year == 2019:
        fechafinal += 'dos mil diecinueve'
    if fecha.year == 2020:
        fechafinal += 'dos mil veinte'
    if fecha.year == 2021:
        fechafinal += 'dos mil veintiuno'
    if fecha.year == 2022:
        fechafinal += 'dos mil veintidos'
    if fecha.year == 2023:
        fechafinal += 'dos mil veintitres'
    if fecha.year == 2024:
        fechafinal += 'dos mil veinticuatro'
    if fecha.year == 2025:
        fechafinal += 'dos mil veinticinco'
    if fecha.year == 2026:
        fechafinal += 'dos mil veintiseis'
    if fecha.year == 2027:
        fechafinal += 'dos mil veintisiete'
    if fecha.year == 2028:
        fechafinal += 'dos mil veintiocho'
    if fecha.year == 2029:
        fechafinal += 'dos mil veintinueve'
    if fecha.year == 2030:
        fechafinal += 'dos mil treinta'
    return fechafinal

def fechaletra_corta2(fecha):
    fechafinal = ''
    if fecha.day == 1:
        fechafinal += 'al primer (1) día '
    elif fecha.day == 2:
        fechafinal += 'a los dos (2) días '
    elif fecha.day == 3:
        fechafinal += 'a los tres (3) días '
    elif fecha.day == 4:
        fechafinal += 'a los cuatro (4) días '
    elif fecha.day == 5:
        fechafinal += 'a los cinco (5) días '
    elif fecha.day == 6:
        fechafinal += 'a los seis (6) días '
    elif fecha.day == 7:
        fechafinal += 'a los siete (7) días '
    elif fecha.day == 8:
        fechafinal += 'a los ocho (8) días '
    elif fecha.day == 9:
        fechafinal += 'a los nueve (9) días '
    elif fecha.day == 10:
        fechafinal += 'a los diez (10) días '
    elif fecha.day == 11:
        fechafinal += 'a los once (11) días '
    elif fecha.day == 12:
        fechafinal += 'a los doce (12) días '
    elif fecha.day == 13:
        fechafinal += 'a los trece (13) días '
    elif fecha.day == 14:
        fechafinal += 'a los catorce (14) días '
    elif fecha.day == 15:
        fechafinal += 'a los quince (15) días '
    elif fecha.day == 16:
        fechafinal += 'a los dieciseis (16) días '
    elif fecha.day == 17:
        fechafinal += 'a los diecisiete (17) días '
    elif fecha.day == 18:
        fechafinal += 'a los dieciocho (18) días '
    elif fecha.day == 19:
        fechafinal += 'a los diecinueve (19) días '
    elif fecha.day == 20:
        fechafinal += 'a los veinte (20) días '
    elif fecha.day == 21:
        fechafinal += 'a los veintiun (21) días '
    elif fecha.day == 22:
        fechafinal += 'a los veintidos (22) días '
    elif fecha.day == 23:
        fechafinal += 'a los veintitres (23) días '
    elif fecha.day == 24:
        fechafinal += 'a los veinticuatro (24) días '
    elif fecha.day == 25:
        fechafinal += 'a los veinticinco (25) días '
    elif fecha.day == 26:
        fechafinal += 'a los veintiseis (26) días '
    elif fecha.day == 27:
        fechafinal += 'a los veintisiete (27) días '
    elif fecha.day == 28:
        fechafinal += 'a los veintiocho (28) días '
    elif fecha.day == 29:
        fechafinal += 'a los veintinueve (29) días '
    elif fecha.day == 30:
        fechafinal += 'a los treinta (30) días '
    elif fecha.day == 31:
        fechafinal += 'a los treinta y un (31) días '
    if fecha.month == 1:
        fechafinal += 'del mes de Enero del '
    if fecha.month == 2:
        fechafinal += 'del mes de Febrero del '
    if fecha.month == 3:
        fechafinal += 'del mes de Marzo del '
    if fecha.month == 4:
        fechafinal += 'del mes de Abril del '
    if fecha.month == 5:
        fechafinal += 'del mes de Mayo del '
    if fecha.month == 6:
        fechafinal += 'del mes de Junio del '
    if fecha.month == 7:
        fechafinal += 'del mes de Julio del '
    if fecha.month == 8:
        fechafinal += 'del mes de Agosto del '
    if fecha.month == 9:
        fechafinal += 'del mes de Septiembre del '
    if fecha.month == 10:
        fechafinal += 'del mes de Octubre del '
    if fecha.month == 11:
        fechafinal += 'del mes de Noviembre del '
    if fecha.month == 12:
        fechafinal += 'del mes de Diciembre del '
    if fecha.year == 1998:
        fechafinal += 'mil novecientos noventa y ocho'
    if fecha.year == 1999:
        fechafinal += 'mil novecientos noventa y nueve'
    if fecha.year == 2000:
        fechafinal += 'dos mil'
    if fecha.year == 2001:
        fechafinal += 'dos mil uno'
    if fecha.year == 2002:
        fechafinal += 'dos mil dos'
    if fecha.year == 2003:
        fechafinal += 'dos mil tres'
    if fecha.year == 2004:
        fechafinal += 'dos mil cuatro'
    if fecha.year == 2005:
        fechafinal += 'dos mil cinco'
    if fecha.year == 2006:
        fechafinal += 'dos mil seis'
    if fecha.year == 2007:
        fechafinal += 'dos mil siete'
    if fecha.year == 2008:
        fechafinal += 'dos mil ocho'
    if fecha.year == 2009:
        fechafinal += 'dos mil nueve'
    if fecha.year == 2010:
        fechafinal += 'dos mil diez'
    if fecha.year == 2011:
        fechafinal += 'dos mil once'
    if fecha.year == 2012:
        fechafinal += 'dos mil doce'
    if fecha.year == 2013:
        fechafinal += 'dos mil trece'
    if fecha.year == 2014:
        fechafinal += 'dos mil catorce'
    if fecha.year == 2015:
        fechafinal += 'dos mil quince'
    if fecha.year == 2016:
        fechafinal += 'dos mil dieciseis'
    if fecha.year == 2017:
        fechafinal += 'dos mil diecisiete'
    if fecha.year == 2018:
        fechafinal += 'dos mil dieciocho'
    if fecha.year == 2019:
        fechafinal += 'dos mil diecinueve'
    if fecha.year == 2020:
        fechafinal += 'dos mil veinte'
    if fecha.year == 2021:
        fechafinal += 'dos mil veintiuno'
    if fecha.year == 2022:
        fechafinal += 'dos mil veintidos'
    if fecha.year == 2023:
        fechafinal += 'dos mil veintitres'
    if fecha.year == 2024:
        fechafinal += 'dos mil veinticuatro'
    if fecha.year == 2025:
        fechafinal += 'dos mil veinticinco'
    if fecha.year == 2026:
        fechafinal += 'dos mil veintiseis'
    if fecha.year == 2027:
        fechafinal += 'dos mil veintisiete'
    if fecha.year == 2028:
        fechafinal += 'dos mil veintiocho'
    if fecha.year == 2029:
        fechafinal += 'dos mil veintinueve'
    if fecha.year == 2030:
        fechafinal += 'dos mil treinta'
    return fechafinal

def fechaletra_corta3(fecha):
    fechafinal = ''
    if fecha.day == 1:
        fechafinal += 'uno (1) '
    elif fecha.day == 2:
        fechafinal += 'dos (2) '
    elif fecha.day == 3:
        fechafinal += 'tres (3) '
    elif fecha.day == 4:
        fechafinal += 'cuatro (4) '
    elif fecha.day == 5:
        fechafinal += 'cinco (5) '
    elif fecha.day == 6:
        fechafinal += 'seis (6) '
    elif fecha.day == 7:
        fechafinal += 'siete (7) '
    elif fecha.day == 8:
        fechafinal += 'ocho (8) '
    elif fecha.day == 9:
        fechafinal += 'nueve (9) '
    elif fecha.day == 10:
        fechafinal += 'diez (10) '
    elif fecha.day == 11:
        fechafinal += 'once (11) '
    elif fecha.day == 12:
        fechafinal += 'doce (12) '
    elif fecha.day == 13:
        fechafinal += 'trece (13) '
    elif fecha.day == 14:
        fechafinal += 'catorce (14) '
    elif fecha.day == 15:
        fechafinal += 'quince (15) '
    elif fecha.day == 16:
        fechafinal += 'dieciseis (16) '
    elif fecha.day == 17:
        fechafinal += 'diecisiete (17) '
    elif fecha.day == 18:
        fechafinal += 'dieciocho (18) '
    elif fecha.day == 19:
        fechafinal += 'diecinueve (19) '
    elif fecha.day == 20:
        fechafinal += 'veinte (20) '
    elif fecha.day == 21:
        fechafinal += 'veintiuno (21) '
    elif fecha.day == 22:
        fechafinal += 'veintidos (22) '
    elif fecha.day == 23:
        fechafinal += 'veintitres (23) '
    elif fecha.day == 24:
        fechafinal += 'veinticuatro (24) '
    elif fecha.day == 25:
        fechafinal += 'veinticinco (25) '
    elif fecha.day == 26:
        fechafinal += 'veintiseis (26) '
    elif fecha.day == 27:
        fechafinal += 'veintisiete (27) '
    elif fecha.day == 28:
        fechafinal += 'veintiocho (28) '
    elif fecha.day == 29:
        fechafinal += 'veintinueve (29) '
    elif fecha.day == 30:
        fechafinal += 'treinta (30) '
    elif fecha.day == 31:
        fechafinal += 'treinta y uno (31) '
    if fecha.month == 1:
        fechafinal += 'de Enero del '
    elif fecha.month == 2:
        fechafinal += 'de Febrero del '
    elif fecha.month == 3:
        fechafinal += 'de Marzo del '
    elif fecha.month == 4:
        fechafinal += 'de Abril del '
    elif fecha.month == 5:
        fechafinal += 'de Mayo del '
    elif fecha.month == 6:
        fechafinal += 'de Junio del '
    elif fecha.month == 7:
        fechafinal += 'de Julio del '
    elif fecha.month == 8:
        fechafinal += 'de Agosto del '
    elif fecha.month == 9:
        fechafinal += 'de Septiembre del '
    elif fecha.month == 10:
        fechafinal += 'de Octubre del '
    elif fecha.month == 11:
        fechafinal += 'de Noviembre del '
    elif fecha.month == 12:
        fechafinal += 'de Diciembre del '
    if fecha.year == 1998:
        fechafinal += 'mil novecientos noventa y ocho'
    if fecha.year == 1999:
        fechafinal += 'mil novecientos noventa y nueve'
    if fecha.year == 2000:
        fechafinal += 'dos mil'
    if fecha.year == 2001:
        fechafinal += 'dos mil uno'
    if fecha.year == 2002:
        fechafinal += 'dos mil dos'
    if fecha.year == 2003:
        fechafinal += 'dos mil tres'
    if fecha.year == 2004:
        fechafinal += 'dos mil cuatro'
    if fecha.year == 2005:
        fechafinal += 'dos mil cinco'
    if fecha.year == 2006:
        fechafinal += 'dos mil seis'
    if fecha.year == 2007:
        fechafinal += 'dos mil siete'
    if fecha.year == 2008:
        fechafinal += 'dos mil ocho'
    if fecha.year == 2009:
        fechafinal += 'dos mil nueve'
    if fecha.year == 2010:
        fechafinal += 'dos mil diez'
    if fecha.year == 2011:
        fechafinal += 'dos mil once'
    if fecha.year == 2012:
        fechafinal += 'dos mil doce'
    if fecha.year == 2013:
        fechafinal += 'dos mil trece'
    if fecha.year == 2014:
        fechafinal += 'dos mil catorce'
    if fecha.year == 2015:
        fechafinal += 'dos mil quince'
    if fecha.year == 2016:
        fechafinal += 'dos mil dieciseis'
    if fecha.year == 2017:
        fechafinal += 'dos mil diecisiete'
    if fecha.year == 2018:
        fechafinal += 'dos mil dieciocho'
    if fecha.year == 2019:
        fechafinal += 'dos mil diecinueve'
    if fecha.year == 2020:
        fechafinal += 'dos mil veinte'
    if fecha.year == 2021:
        fechafinal += 'dos mil veintiuno'
    if fecha.year == 2022:
        fechafinal += 'dos mil veintidos'
    if fecha.year == 2023:
        fechafinal += 'dos mil veintitres'
    if fecha.year == 2024:
        fechafinal += 'dos mil veinticuatro'
    if fecha.year == 2025:
        fechafinal += 'dos mil veinticinco'
    if fecha.year == 2026:
        fechafinal += 'dos mil veintiseis'
    if fecha.year == 2027:
        fechafinal += 'dos mil veintisiete'
    if fecha.year == 2028:
        fechafinal += 'dos mil veintiocho'
    if fecha.year == 2029:
        fechafinal += 'dos mil veintinueve'
    if fecha.year == 2030:
        fechafinal += 'dos mil treinta'
    return fechafinal


def fields_model(classname, app):
    try:
        d = locals()
        exec('from %s.models import %s' % (app, classname), globals(), d)
        # exec('from %s.models import %s' % (app, classname))
        fields = eval(classname + '._meta.get_fields()')
        return fields
    except:
        return []


def field_default_value_model(field):
    try:
        value = str(field)
        return value if 'django.db.models.fields.NOT_PROVIDED' not in value else ''
    except:
        return ''


def sumar_hora(hora_1, hora_2):
    minuto_aux = 0
    hora_aux = 0
    horas_letras_aux = ''
    minutos_letras_aux = ''
    segundos_letras_aux = ''

    lista1 = hora_1.split(":")
    hora1 = int(lista1[0])
    minuto1 = int(lista1[1])
    segundo1 = int(lista1[2])

    lista2 = hora_2.split(":")
    hora2 = int(lista2[0])
    minuto2 = int(lista2[1])
    segundo2 = int(lista2[2])
    # sumar segundos
    segundos = int(segundo1) + int(segundo2)
    if segundos >= 60:
        segundos = segundos - 60
        minuto_aux = 1

    # sumar minutos
    minutos = int(minuto1) + int(minuto2)
    if minutos >= 60:
        minutos = minutos - 60 + minuto_aux
        hora_aux = 1

    # sumar horas
    horas = hora1 + hora2 + hora_aux

    if segundos < 9:
        segundos_letras_aux = "0" + str(segundos)
    else:
        segundos_letras_aux = str(segundos)

    if minutos < 9:
        minutos_letras_aux = "0" + str(minutos)
    else:
        minutos_letras_aux = str(minutos)

    if horas < 9:
        horas_letras_aux = "0" + str(horas)
    else:
        horas_letras_aux = str(horas)

    resultado = horas_letras_aux + ":" + minutos_letras_aux + ":" + segundos_letras_aux
    return str(resultado)


def variable_valor(variable):
    from sga.models import VariablesGlobales
    if cache.has_key(f"variable_global_{variable.upper()}"):
        return cache.get(f"variable_global_{variable.upper()}")
    else:
        try:
            eVariablesGlobal = VariablesGlobales.objects.db_manager("sga_select").values("tipodato", "valor").get(status=True,variable__exact=variable)
        except ObjectDoesNotExist:
            eVariablesGlobal = None
        valor = None
        if eVariablesGlobal:
            if eVariablesGlobal['tipodato'] == 1:
                valor = eVariablesGlobal['valor']
            elif eVariablesGlobal['tipodato'] == 2:
                valor = int(eVariablesGlobal['valor'])
            elif eVariablesGlobal['tipodato'] == 3:
                valor = float(eVariablesGlobal['valor'])
            elif eVariablesGlobal['tipodato'] == 4:
                valor = eVariablesGlobal['valor'].lower() in ("yes", "true", "t", "1", "si")
            elif eVariablesGlobal['tipodato'] == 5:
                valor = convertir_fecha(eVariablesGlobal['valor'])
            elif eVariablesGlobal['tipodato'] == 6:
                valor = eVariablesGlobal['valor'].split(',') if not eVariablesGlobal['valor'] == "" else []
        cache.set(f"variable_global_{variable.upper()}", valor, 60 * 60 * 60)
        return valor

def null_to_decimal(valor, decimales=None):
    if not decimales is None and not valor is None:
        if decimales > 0:
            sql = """SELECT round(%s::numeric,%s)""" % (valor, decimales)
            cursor = connections['sga_select'].cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            return float(results[0][0])
            # return float(Decimal(repr(valor) if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1')) if valor else 0)
            # return float(Decimal(valor.__str__() if valor else 0).quantize(Decimal('.' + ''.zfill(decimales - 1) + '1'), rounding=ROUND_HALF_UP) if valor else 0)
        else:
            sql = """SELECT round(%s::numeric,%s)""" % (valor, 0)
            cursor = connections['sga_select'].cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            return float(results[0][0])
            # return float(Decimal(valor.__str__() if valor else 0).quantize(Decimal('0')))
    return valor if valor else 0

def actualiza_asistencia(materiaasignada_id):
    from sga.models import MateriaAsignada
    vAsistenciafinal = 100
    if materiaasignada := MateriaAsignada.objects.db_manager("sga_select").values("sinasistencia", "matricula__inscripcion__coordinacion_id", "materia__sinasistencia", "fechaasignacion", "materia__fechafinasistencias").filter(pk=materiaasignada_id).exclude(sinasistencia=True).exclude(materia__sinasistencia=True).first():
            vAsistenciafinal = porciento_asistencia(materiaasignada_id=materiaasignada_id, sinasistencia=materiaasignada['sinasistencia'], fechaasignacion=materiaasignada['fechaasignacion'], materia_fechafinasistencias=materiaasignada['materia__fechafinasistencias'], coordinacion_id=materiaasignada['matricula__inscripcion__coordinacion_id'])
    MateriaAsignada.objects.db_manager("default").filter(pk=materiaasignada_id).exclude(asistenciafinal=100).update(asistenciafinal=vAsistenciafinal)

def porciento_asistencia(materiaasignada_id, sinasistencia, fechaasignacion, materia_fechafinasistencias, coordinacion_id):
    from sga.models import AsistenciaLeccion
    if coordinacion_id == 7:
        asistencias = AsistenciaLeccion.objects.db_manager("sga_select").values("id", "asistio").filter(materiaasignada_id=materiaasignada_id, status=True, leccion__clase__status=True, leccion__clase__activo=True, leccion__status=True).order_by("id", "asistio").distinct()
    else:
        asistencias = AsistenciaLeccion.objects.db_manager("sga_select").values("id", "asistio").filter(materiaasignada_id=materiaasignada_id, leccion__status=True, leccion__clase__status=True, leccion__clase__activo=True, leccion__fecha__gte=fechaasignacion, leccion__fecha__lte=materia_fechafinasistencias, status=True).order_by("id", "asistio").distinct()
    totalregistros = asistencias.count()
    if totalregistros > 0:
        real = asistencias.filter(asistio=True).count()
        asitencia_final = null_to_decimal(((real * 100) / totalregistros), 0)
        return asitencia_final if asitencia_final <= 100 else 100
    return 100


def null_to_numeric(valor, decimales=None):
    if decimales:
        return round((valor if valor else 0), decimales)
    return valor if valor else 0





class Round2(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s::numeric, 2)'


class Round4(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s::numeric, 4)'


class Round0(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s::numeric, 0)'


def convertir_fecha_invertida_hora(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return datetime(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]), int(s.split(sep)[3]),
                    int(s.split(sep)[4]))


def convertir_fecha_hora(s):
    fecha = s.split(' ')[0]
    hora = s.split(' ')[1]
    if '/' in fecha:
        sep = ':'
    elif '-' in fecha:
        sep = '-'
    else:
        sep = ':'
    return datetime(int(fecha.split(sep)[2]), int(fecha.split(sep)[1]), int(fecha.split(sep)[0]),
                    int(hora.split(':')[0]), int(hora.split(':')[1]))


def convertir_fecha_hora_invertida(s):
    fecha = s.split(' ')[0]
    hora = s.split(' ')[1]
    if '/' in fecha:
        sep = ':'
    elif '-' in fecha:
        sep = '-'
    else:
        sep = ':'
    return datetime(int(fecha.split(sep)[0]), int(fecha.split(sep)[1]), int(fecha.split(sep)[2]),
                    int(hora.split(':')[0]), int(hora.split(':')[1]))


def restar_hora(hora1, hora2):
    formato = "%H:%M:%S"
    h1 = datetime.strptime(hora1, formato)
    h2 = datetime.strptime(hora2, formato)
    resultado = h1 - h2
    return str(resultado)


def years_ago(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year - years, month, day)
    except Exception as ex:
        pass
        return years_ago(years, stardate, day)


def years_future(years, stardate, day=None):
    if day:
        day -= 1
    else:
        day = stardate.day
    month = stardate.month
    year = stardate.year
    try:
        return date(year + years, month, day)
    except Exception as ex:
        pass
        return years_ago(years, stardate, day)


def calcula_edad(fnacimiento):
    hoy = date.today()
    return hoy.year - fnacimiento.year - ((hoy.month, hoy.day) < (fnacimiento.month, fnacimiento.day))


def calcula_edad_fn_fc(fnacimiento, fechacalculo):
    return fechacalculo.year - fnacimiento.year - ((fechacalculo.month, fechacalculo.day) < (fnacimiento.month, fnacimiento.day))


def suma_dias_habiles(fecha, dias):
    try:
        h = dias
        ds = 5 - fecha.weekday()  # distancia al sabado
        s = 0
        if h >= ds:
            s = s + 2
            h = h - ds

        s = s + h / 5 * 2
        return datetime.fromordinal(fecha.toordinal() + int(dias) + int(s))
    except Exception as ex:
        return datetime.now().date()


class ModeloBase(models.Model):
    """ Modelo base para todos los modelos del proyecto """
    from django.contrib.auth.models import User
    status = models.BooleanField(default=True)
    usuario_creacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    usuario_modificacion = models.ForeignKey(User, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        usuario = None
        fecha_modificacion = datetime.now()
        fecha_creacion = None
        update_fields = None
        if len(args):
            usuario = args[0].user.id
        for key, value in kwargs.items():
            if 'usuario_id' == key:
                usuario = value
            if 'fecha_modificacion' == key:
                fecha_modificacion = value
            if 'fecha_creacion' == key:
                fecha_creacion = value
            if 'update_fields' == key:
                update_fields = value
        if self.id:
            self.usuario_modificacion_id = usuario if usuario else ADMINISTRADOR_ID
            self.fecha_modificacion = fecha_modificacion
            if update_fields is not None:
                update_fields = [*update_fields, 'usuario_modificacion_id', 'fecha_modificacion']
                kwargs['update_fields'] = list(set(update_fields))
        else:
            self.usuario_creacion_id = usuario if usuario else ADMINISTRADOR_ID
            self.fecha_creacion = fecha_modificacion
            if fecha_creacion:
                self.fecha_creacion = fecha_creacion
        models.Model.save(self, update_fields=update_fields)

    class Meta:
        abstract = True


def trimestre(mes):
    if mes >= 1 and mes <= 3:
        return 'PRIMER TRIMESTRE'
    if mes >= 4 and mes <= 6:
        return 'SEGUNDO TRIMESTRE'
    if mes >= 7 and mes <= 9:
        return 'TERCER TRIMESTRE'
    if mes >= 10 and mes <= 12:
        return 'CUARTO TRIMESTRE'


def validar_ldap(usuario, clave, persona):
    from sga.models import UsuarioLdap
    if not UsuarioLdap.objects.filter(usuario_id=persona.usuario_id, status=True).exists():
        # if not UsuarioLdap.objects.filter(usuario_id=persona.usuario_id, status=True).exists():
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.emailinst.split('@')[0]
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        else:
            # no lo encontro
            nombres = persona.nombres
            apellidos = persona.apellido1 + ' ' + persona.apellido2
            nombre_completo = nombres + apellidos
            mail = persona.emailinst
            conn.add(busqueda, ['inetOrgPerson'],
                     {'givenName': nombres, 'sn': apellidos, 'uid': usuario_aux, 'cn': nombre_completo, 'mail': mail,
                      'userPassword': clave})
        conn.unbind()
        usuarioldap = UsuarioLdap(usuario=persona.usuario)
        usuarioldap.save()
    # else:
    #     from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
    #     server = Server('10.142.0.39', port=389, get_info=ALL)
    #     conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
    #     usuario_aux = persona.emailinst.split('@')[0]
    #     busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
    #     if conn.search(busqueda, '(objectclass=person)'):
    #         # lo encontro
    #         conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
    #     conn.unbind()


def validar_ldaptic(usuario, clave, persona):
    from sga.models import UsuarioLdap
    if not UsuarioLdap.objects.filter(usuario=persona.usuario, status=True).exists():
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.usuario.username
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        else:
            # no lo encontro
            nombres = persona.nombres
            apellidos = persona.apellido1 + ' ' + persona.apellido2
            nombre_completo = nombres + apellidos
            mail = persona.emailinst
            conn.add(busqueda, ['inetOrgPerson'],
                     {'givenName': nombres, 'sn': apellidos, 'uid': usuario_aux, 'cn': nombre_completo, 'mail': mail,
                      'userPassword': clave})
        conn.unbind()
        usuarioldap = UsuarioLdap(usuario=persona.usuario)
        usuarioldap.save()
    else:
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.usuario.username
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        conn.unbind()


def validar_ldap_reseteo(usuario, clave, persona):
    from sga.models import UsuarioLdap
    if UsuarioLdap.objects.filter(usuario=persona.usuario, status=True).exists():
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.emailinst.split('@')[0]
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        conn.unbind()
    else:
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.emailinst.split('@')[0]
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        else:
            # no lo encontro
            nombres = persona.nombres
            apellidos = persona.apellido1 + ' ' + persona.apellido2
            nombre_completo = nombres + apellidos
            mail = persona.emailinst
            conn.add(busqueda, ['inetOrgPerson'],
                     {'givenName': nombres, 'sn': apellidos, 'uid': usuario_aux, 'cn': nombre_completo, 'mail': mail,
                      'userPassword': clave})
        conn.unbind()
        usuarioldap = UsuarioLdap(usuario=persona.usuario)
        usuarioldap.save()


def validar_ldap_aux(usuario, clave, persona):
    from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
    server = Server('10.142.0.39', port=389, get_info=ALL)
    conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
    usuario_aux = persona.emailinst.split('@')[0]
    busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
    if conn.search(busqueda, '(objectclass=person)'):
        # lo encontro
        conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
    else:
        # no lo encontro
        nombres = persona.nombres
        apellidos = persona.apellido1 + ' ' + persona.apellido2
        nombre_completo = nombres + apellidos
        mail = persona.emailinst
        conn.add(busqueda, ['inetOrgPerson'],
                 {'givenName': nombres, 'sn': apellidos, 'uid': usuario_aux, 'cn': nombre_completo, 'mail': mail,
                  'userPassword': clave})
    conn.unbind()


def dia_semana_ennumero_fecha(fecha):
    dicdias = {'MONDAY': '2', 'TUESDAY': '3', 'WEDNESDAY': '4', 'THURSDAY': '5', 'FRIDAY': '6', 'SATURDAY': '7',
               'SUNDAY': '1'}
    dia = dicdias[fecha.strftime('%A').upper()]
    return int(dia)


def dia_semana_enletras_fecha(fecha):
    dicdias = {'MONDAY': 'Lunes', 'TUESDAY': 'Martes', 'WEDNESDAY': 'Miercoles', 'THURSDAY': 'Jueves',
               'FRIDAY': 'Viernes', 'SATURDAY': 'Sabado', 'SUNDAY': 'Domingo'}
    dia = dicdias[fecha.strftime('%A').upper()]
    return dia


def nivel_enletra_malla(orden):
    if orden == 1:
        nivel = '1RO'
    elif orden == 2:
        nivel = '2DO'
    elif orden == 3:
        nivel = '3RO'
    elif orden == 4:
        nivel = '4TO'
    elif orden == 5:
        nivel = '5TO'
    elif orden == 6:
        nivel = '6TO'
    elif orden == 7:
        nivel = '7MO'
    elif orden == 8:
        nivel = '8VO'
    elif orden == 9:
        nivel = '9NO'
    elif orden == 10:
        nivel = '10MO'
    elif orden == 11:
        nivel = '11RO'
    elif orden == 12:
        nivel = '12DO'
    elif orden == 13:
        nivel = '13RO'
    elif orden == 14:
        nivel = '14TO'
    else:
        nivel = ''
    return nivel


def paralelo_enletra_nivel(orden):
    if orden == 1:
        nivel = 'PRIMERO '
    elif orden == 2:
        nivel = 'SEGUNDO'
    elif orden == 3:
        nivel = 'TERCERO'
    elif orden == 4:
        nivel = 'CUARTO'
    elif orden == 5:
        nivel = 'QUINTO'
    elif orden == 6:
        nivel = 'SEXTO'
    elif orden == 7:
        nivel = 'SEPTIMO '
    elif orden == 8:
        nivel = 'OCTAVO'
    elif orden == 9:
        nivel = 'NOVENO'
    elif orden == 10:
        nivel = 'DECIMO'
    else:
        nivel = 'NO APLICA'
    return nivel


# NUMERO A LETRAS
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def convertirfecha(fecha):
    try:
        return date(int(fecha[6:10]), int(fecha[3:5]), int(fecha[0:2]))
    except Exception as ex:
        return datetime.now().date()


def convertirfechahora(fecha):
    try:
        return datetime(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]), int(fecha[11:13]), int(fecha[14:16]),
                        int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfechahorainvertida(fecha):
    try:
        return datetime(int(fecha[6:10]), int(fecha[3:5]), int(fecha[0:2]), int(fecha[11:13]), int(fecha[14:16]),
                        int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()


MAX_NUMERO = 999999999999
MONEDA_SINGULAR = 'dolar'
MONEDA_PLURAL = 'dolares'
CENTIMOS_SINGULAR = 'centavo'
CENTIMOS_PLURAL = 'centavos'

UNIDADES = (
    'cero',
    'uno',
    'dos',
    'tres',
    'cuatro',
    'cinco',
    'seis',
    'siete',
    'ocho',
    'nueve'
)

DECENAS = (
    'diez',
    'once',
    'doce',
    'trece',
    'catorce',
    'quince',
    'dieciseis',
    'diecisiete',
    'dieciocho',
    'diecinueve'
)

DIEZ_DIEZ = (
    'cero',
    'diez',
    'veinte',
    'treinta',
    'cuarenta',
    'cincuenta',
    'sesenta',
    'setenta',
    'ochenta',
    'noventa'
)

CIENTOS = (
    '_',
    'ciento',
    'doscientos',
    'trescientos',
    'cuatroscientos',
    'quinientos',
    'seiscientos',
    'setecientos',
    'ochocientos',
    'novecientos'
)


def leer_decenas(numero):
    if numero < 10:
        return UNIDADES[numero]
    decena, unidad = divmod(numero, 10)
    if unidad == 0:
        resultado = DIEZ_DIEZ[decena]
    else:
        if numero <= 19:
            resultado = DECENAS[unidad]
        elif numero <= 29:
            resultado = 'veinti%s' % UNIDADES[unidad]
        else:
            resultado = DIEZ_DIEZ[decena]
            if unidad > 0:
                resultado = '%s y %s' % (resultado, UNIDADES[unidad])
    return resultado


def leer_centenas(numero):
    centena, decena = divmod(numero, 100)
    if numero == 0:
        resultado = 'cien'
    else:
        resultado = CIENTOS[centena]
        if decena > 0:
            resultado = '%s %s' % (resultado, leer_decenas(decena))
    return resultado


def leer_miles(numero):
    millar, centena = divmod(numero, 1000)
    resultado = ''
    if millar == 1:
        resultado = ''
    if 2 <= millar <= 9:
        resultado = UNIDADES[millar]
    elif 10 <= millar <= 99:
        resultado = leer_decenas(millar)
    elif 100 <= millar <= 999:
        resultado = leer_centenas(millar)
    resultado = '%s mil' % resultado
    if centena > 0:
        resultado = '%s %s' % (resultado, leer_centenas(centena))
    return resultado


def leer_millones(numero):
    millon, millar = divmod(numero, 1000000)
    resultado = ''
    if millon == 1:
        resultado = ' un millon '
    if 2 <= millon <= 9:
        resultado = UNIDADES[millon]
    elif 10 <= millon <= 99:
        resultado = leer_decenas(millon)
    elif 100 <= millon <= 999:
        resultado = leer_centenas(millon)
    if millon > 1:
        resultado = '%s millones' % resultado
    if (millar > 0) and (millar <= 999):
        resultado = '%s %s' % (resultado, leer_centenas(millar))
    elif (millar >= 1000) and (millar <= 999999):
        resultado = '%s %s' % (resultado, leer_miles(millar))
    return resultado


def leer_millardos(numero):
    millardo, millon = divmod(numero, 1000000)
    return '%s millones %s' % (leer_miles(millardo), leer_millones(millon))


def numero_a_letras(numero):
    numero_entero = int(numero)
    if numero_entero > MAX_NUMERO:
        raise OverflowError('Número demasiado alto')
    if numero_entero < 0:
        return 'menos %s' % numero_a_letras(abs(numero))
    letras_decimal = ''
    parte_decimal = int(round((abs(numero) - abs(numero_entero)) * 100))
    if parte_decimal > 9:
        letras_decimal = 'punto %s' % numero_a_letras(parte_decimal)
    elif parte_decimal > 0:
        letras_decimal = 'punto cero %s' % numero_a_letras(parte_decimal)
    if numero_entero <= 99:
        resultado = leer_decenas(numero_entero)
    elif numero_entero <= 999:
        resultado = leer_centenas(numero_entero)
    elif numero_entero <= 999999:
        resultado = leer_miles(numero_entero)
    elif numero_entero <= 999999999:
        resultado = leer_millones(numero_entero)
    else:
        resultado = leer_millardos(numero_entero)
    resultado = resultado.replace('uno mil', 'un mil')
    resultado = resultado.strip()
    resultado = resultado.replace(' _ ', ' ')
    resultado = resultado.replace('  ', ' ')
    if parte_decimal > 0:
        resultado = '%s %s' % (resultado, letras_decimal)
    return resultado


def moneda_a_letras(numero):
    if '.' in numero:
        posicion = numero.split('.')
        numero_entero = int(posicion[0])
        parte_decimal = 0
        if posicion[1] != '':
            parte_decimal = int(posicion[1])
    else:
        numero_entero = int(numero)
        parte_decimal = 0
    centimos = ''
    if parte_decimal == 1:
        centimos = CENTIMOS_SINGULAR
    else:
        centimos = CENTIMOS_PLURAL
    moneda = ''
    if numero_entero == 1:
        moneda = MONEDA_SINGULAR
    else:
        moneda = MONEDA_PLURAL
    letras = numero_a_letras(numero_entero)
    letras = letras.replace('uno', 'un')
    letras_decimal = u'%s/100 DOLARES DE LOS ESTADOS UNIDOS DE NORTE AMÉRICA' % (str(parte_decimal))
    letras = u'%s %s' % (letras, letras_decimal)
    return letras


def fecha_letra_formato_fecha(valor):
    if ':' in valor:
        sep = ':'
    elif '-' in valor:
        sep = '-'
    else:
        sep = '/'
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
           "Noviembre", "Diciembre"]
    d = int(valor.split(sep)[2])
    m = int(valor.split(sep)[1])
    a = int(valor.split(sep)[0])
    if d == 1:
        return u"al %s día del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))
    else:
        return u"a los %s días del mes de %s del %s" % (numero_a_letras(d), str(mes[m - 1]), numero_a_letras(a))


def leer_fecha_hora_letra_formato_fecha_hora(fecha, hora=None, isDay=True):
    sep_h = None
    if hora:
        if ':' in hora:
            sep_h = ':'
    sep_d = None
    if '-' in fecha:
        sep_d = '-'
    else:
        sep_d = '/'
    mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    d = fecha.split(sep_d)[2]
    m = fecha.split(sep_d)[1]
    a = fecha.split(sep_d)[0]
    if sep_h:
        hh = hora.split(sep_h)[0]
        mm = hora.split(sep_h)[1]

    s = f"{d} de {str(mes[int(m) - 1])} del {a}"
    if isDay:
        s = f"{dia_semana_enletras_fecha(datetime.strptime(fecha, f'%Y{sep_d}%m{sep_d}%d'))}, {s}"
    if hora:
        if int(hh) == 1:
            s = f"{s} a la {hh}:{mm}"
        else:
            s = f"{s} a las {hh}:{mm}"
    return s


def querymysqlsakai(sql, resultados=False):
    import mysql.connector
    # mydb = mysql.connector.connect(
    #     host="181.188.214.109",
    #     user="sgauser",
    #     passwd="tum4ch0yd0r1ma?",
    #     database="unemisakai"
    # )
    mydb = mysql.connector.connect(
        host="10.10.100.189",
        user="sakai",
        passwd="Em3l3c2019**",
        database="unemisakai"
    )
    # mydb = mysql.connector.connect(
    #     host="181.188.214.109",
    #     user="sgauser",
    #     passwd="tum4ch0yd0r1ma?",
    #     database="unemisakai"
    # )
    # mydb = mysql.connector.connect(
    #     host="181.188.214.109",
    #     user="sgauser",
    #     passwd="tum4ch0yd0r1ma?",
    #     database="reporte-examen"
    # )
    # mydb = mysql.connector.connect(
    #     host="186.5.39.174",
    #     user="gestion",
    #     passwd="Un3m1sakai?",
    #     database="sakai_prueba1"
    # )
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    if resultados:
        lista = mycursor.fetchall()
    else:
        mydb.commit()
    mycursor.close()
    mydb.close()
    if resultados:
        return lista


def querymysqlconsulta(sql, resultados=False):
    import mysql.connector
    mydb = mysql.connector.connect(
        host="181.188.214.109",
        user="sgauser",
        passwd="tum4ch0yd0r1ma?",
        database="reporte-examen"
    )
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    if resultados:
        lista = mycursor.fetchall()
    else:
        mydb.commit()
    mycursor.close()
    mydb.close()
    if resultados:
        return lista


def querymysqlmoodle(sql, resultados=False):
    import mysql.connector
    mydb = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        passwd="",
        database="moodle_bd"
    )
    mycursor = mydb.cursor()
    mycursor.execute(sql)
    if resultados:
        lista = mycursor.fetchall()
    else:
        mydb.commit()
    mycursor.close()
    mydb.close()
    if resultados:
        return lista


carreras = {
    'COM': u'ADMISION COMUNICACION VIRTUAL',
    'DER': u'ADMISION DERECHO VIRTUAL',
    'ECO': u'ADMISION ECONOMIA VIRTUAL',
    'EDU': u'ADMISION EDUCACION BASICA VIRTUAL',
    'EDI': u'ADMISION EDUCACION INICIAL VIRTUAL',
    'PEDI': u'ADMISION PEDAGOGIA IDIOMAS VIRTUAL',
    'PSC': u'ADMISION PSICOLOGIA VIRTUAL',
    'TICS': u'ADMISION TECNOLOGIAS DE LA INFORMACION VIRTUAL',
    'TRS': u'ADMISION TRABAJO SOCIAL VIRTUAL',
    'TUR': u'ADMISION TURISMO VIRTUAL'}


def extraer_carrera(nombre_materia, listacarreras, listaparalelo):
    extraer_1 = nombre_materia.upper().split('[')
    if extraer_1 and extraer_1.__len__() > 1:
        abreviatura = extraer_1[1].split('_')[0]
        if abreviatura in carreras:
            nombrecarrera = carreras[abreviatura]
            paralelo = extraer_1[1].split(']')[0]
            if not nombrecarrera in listacarreras:
                listacarreras.append(nombrecarrera)
            if not paralelo in listaparalelo:
                listaparalelo.append(paralelo)


def numeroactividades(elemento, lista, numero):
    veces = 0
    for i in lista:
        if numero == 1:
            if elemento == i[0]:
                veces += 1
        if numero == 2:
            if elemento == i[2]:
                veces += 1
    return veces


def numeroactividadesdinamico(elemento, lista, numero, antesesora, numeroantesesora, indiceantesesora):
    veces = 0
    for i in lista:
        if antesesora == 0:
            if elemento == i[numero]:
                veces += 1
        if antesesora == 1:
            if elemento == i[numero] and numeroantesesora == i[indiceantesesora]:
                veces += 1
    return veces


def ultimocodigoactividaddinamico(elemento, lista, numero, indicecodigo, antesesora, numeroantesesora, indiceantesesora):
    veces = 0
    codigo = 0
    for i in lista:
        if antesesora == 0:
            if elemento == i[numero]:
                veces += 1
                if veces == 1:
                    codigo = i[indicecodigo]
        if antesesora == 1:
            if elemento == i[numero] and numeroantesesora == i[indiceantesesora]:
                veces += 1
                if veces == 1:
                    codigo = i[indicecodigo]
    return codigo


def ultimocodigoactividad(elemento, lista, numero):
    veces = 0
    codigo = 0
    for i in lista:
        if numero == 1:
            if elemento == i[0]:
                veces += 1
                if veces == 1:
                    codigo = i[1]
        if numero == 2:
            if elemento == i[2]:
                veces += 1
                if veces == 1:
                    codigo = i[1]
    return codigo


def grafica_barra(titulografica, tituloposx, valores, categorias, mostrarsimboloporcentaje, tieneleyenda, leyenda,
                  barrasagrupadas, coloresindividual, coloresagrupado):
    fontName = 'Helvetica'
    fontSize = 12
    bFontName = 'Helvetica'
    bFontSize = 12

    drawing = Drawing(800, 500)
    bc = VerticalBarChart()
    bc.x = 150
    bc.y = 150

    bc.height = 300
    bc.width = 500

    bc.data = valores
    bc.strokeColor = colors.black
    bc.barSpacing = 3.5
    bc.barWidth = 20
    bc.groupSpacing = 15
    bc.strokeColor = None
    bc.strokeWidth = 0
    bc.barSpacing = 4
    bc.barWidth = 40

    if mostrarsimboloporcentaje:
        bc.barLabelFormat = DecimalFormatter(2, suffix='%')
    else:
        bc.barLabelFormat = '%s'

    bc.barLabels.nudge = 5
    bc.barLabels.fontName = fontName
    bc.barLabels.fontSize = fontSize
    bc.barLabels.dy = 5

    minimo = 0
    maximo = max(max(valores))

    maximo += 1
    bc.valueAxis.valueStep = None
    bc.valueAxis.valueMin = minimo
    bc.valueAxis.valueMax = maximo

    if mostrarsimboloporcentaje:
        bc.valueAxis.valueStep = 10
        bc.valueAxis.labelTextFormat = DecimalFormatter(0, suffix='%')
    else:
        if maximo < 6:
            bc.valueAxis.valueStep = 1
        elif maximo < 10:
            bc.valueAxis.valueStep = 2

    bc.valueAxis.visibleGrid = True
    bc.valueAxis.visibleTicks = True
    bc.valueAxis.strokeWidth = 0
    bc.valueAxis.labels.dx = -10
    bc.valueAxis.gridStrokeColor = colors.black  # PCMYKColor(100, 0, 46, 46)
    bc.valueAxis.gridStrokeWidth = 0.25
    bc.valueAxis.rangeRound = 'both'
    # bc.valueAxis.avoidBoundFrac = None

    bc.valueAxis.labels.fontName = fontName
    bc.valueAxis.labels.fontSize = fontSize

    ind = 0
    if barrasagrupadas:
        for color in coloresagrupado:
            bc.bars[ind].fillColor = color
            ind += 1
    else:
        for color in coloresindividual:
            bc.bars[0, ind].fillColor = color
            ind += 1

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.strokeWidth = 0
    bc.categoryAxis.labels.fontName = bFontName
    bc.categoryAxis.labels.fontSize = bFontSize

    if tieneleyenda:
        legend = Legend()
        legend.alignment = 'right'
        legend.boxAnchor = 'sw'
        legend.columnMaximum = 3
        legend.dx = 8
        legend.dxTextSpace = 4
        legend.dy = 6
        legend.fontSize = 10
        legend.fontName = fontName
        legend.strokeColor = None
        legend.strokeWidth = 0
        legend.subCols.minWidth = 55
        legend.variColumn = 1
        legend.x = 150
        legend.y = 1
        legend.deltay = 10
        legend.colorNamePairs = leyenda
        legend.autoXPadding = 65

    bc.categoryAxis.categoryNames = categorias

    titlegraph = Label()
    titlegraph.boxAnchor = 'nw'
    titlegraph.x = tituloposx
    titlegraph.y = drawing.height
    titlegraph.fontName = fontName
    titlegraph.fontSize = fontSize
    titlegraph._text = titulografica

    drawing.add(titlegraph)
    if tieneleyenda:
        drawing.add(legend)
    drawing.add(bc)

    return drawing


def fechaformatostr(fecha, formato):
    sep = ':' if ':' in fecha else '-' if '-' in fecha else '/'
    if formato.upper() == 'DMA':
        return fecha.split(sep)[2] + sep + fecha.split(sep)[1] + sep + fecha.split(sep)[0]
    else:
        return fecha.split(sep)[0] + sep + fecha.split(sep)[1] + sep + fecha.split(sep)[2]


def email_valido(email):
    # regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    regex = '(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)'
    if re.search(regex, email):
        return True
    else:
        return False


def existen_requisitos_becas(periodoid, tipo):
    from sga.models import BecaRequisitos
    return BecaRequisitos.objects.filter(Q(becatipo__isnull=True) | Q(becatipo_id=tipo), periodo_id=periodoid,
                                         status=True, vigente=True).exists()


def cuenta_email_disponible():
    from sga.models import CUENTAS_CORREOS, AnalisisCuentasCorreos
    for cuenta in CUENTAS_CORREOS:
        email = cuenta[0]
        if email in [0, 8, 9, 10, 11, 12, 13]:
            if AnalisisCuentasCorreos.objects.values("id").filter(cuenta=email, fecha=datetime.now().date()).exists():
                if AnalisisCuentasCorreos.objects.values("id").filter(cuenta=email, fecha=datetime.now().date(),
                                                                      conteo__lt=2000).exists():
                    break
            else:
                break

    return email


def cuenta_email_disponible_para_envio(listacuentascorreo):
    from sga.models import CUENTAS_CORREOS, AnalisisCuentasCorreos
    for cuenta in CUENTAS_CORREOS:
        email = cuenta[0]
        if email in listacuentascorreo:
            if AnalisisCuentasCorreos.objects.values("id").filter(cuenta=email, fecha=datetime.now().date()).exists():
                if AnalisisCuentasCorreos.objects.values("id").filter(cuenta=email, fecha=datetime.now().date(),
                                                                      conteo__lt=2000).exists():
                    break
            else:
                break

    return email


def generar_codigo(last=1, prefix='UNEMI', suffix=None, numberdigits=9, temp=False):
    code = None
    year = datetime.now().strftime('%Y')
    if type(last) == int:
        last = str(last)
    if suffix:
        code = prefix + '-' + suffix + '-' + year + '-' + last.zfill(numberdigits)
    else:
        code = prefix + '-' + year + '-' + last.zfill(numberdigits)
    if temp:
        code = code + '-TEMP'
    return code


def validar_archivo(descripcion, archivo, extensionespermitidas, tamaniopermitido):
    import PyPDF2
    # https://convertlive.com/es/u/convertir/megabytes/a/bytes
    tamanios = {'1MB': 1048576,
                '2MB': 2097152,
                '3MB': 3145728,
                '4MB': 4194304,
                '5MB': 5242880,
                '6MB': 6291456,
                '7MB': 7340032,
                '8MB': 8388608,
                '9MB': 9437184,
                '10MB': 10485760}

    nombrearchivo = archivo._name.split('.')
    tamlista = len(nombrearchivo)
    exte = nombrearchivo[tamlista - 1]

    extensionesPermitidas = [x.lower() for x in extensionespermitidas]

    # * significa cualquier extensión
    if not '*' in extensionesPermitidas:
        if not exte.lower() in extensionesPermitidas:
            mensaje = u"Solo se permiten archivos %s [%s]" % (", ".join(extensionesPermitidas), descripcion)
            return {"estado": "error", "mensaje": mensaje}

    if archivo.size > tamanios[tamaniopermitido.upper()]:
        mensaje = u"Error, el tamaño del archivo es mayor a %s. [%s]" % (tamaniopermitido.upper(), descripcion)
        return {"estado": "error", "mensaje": mensaje}

    if 'pdf' in extensionesPermitidas and exte.lower() == 'pdf':
        try:
            pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
        except Exception as ex:
            mensaje = u"Error, existen problemas con el archivo [%s]" % (descripcion)
            return {"estado": "error", "mensaje": mensaje}

    return {"estado": "OK"}


def contar_palabras(texto):
    import string, re
    CLEANR = re.compile('<.*?>')
    texto = re.sub(CLEANR, '', texto)
    total = sum([i.strip(string.punctuation).isalpha() for i in texto.split()])
    return total


def fecha_letra_rango(inicio, fin):
    from sga.models import MESES_CHOICES
    fecharango = ''
    if inicio.year == fin.year:
        if inicio.month == fin.month:
            if inicio.day == fin.day:
                fecharango = 'el ' + str(inicio.day) + ' de ' + MESES_CHOICES[inicio.month - 1][1].capitalize() + ' del ' + str(inicio.year)
            else:
                fecharango = 'del ' + str(inicio.day) + ' al ' + str(fin.day) + ' de '+ MESES_CHOICES[inicio.month - 1][1].capitalize() + ' del ' + str(inicio.year)
        else:
            fecharango = 'del ' + str(inicio.day) + ' de '+ MESES_CHOICES[inicio.month - 1][1].capitalize() + ' al ' + str(fin.day) + ' de ' + MESES_CHOICES[fin.month - 1][1].capitalize() + ' del ' + str(inicio.year)
    else:
        fecharango = 'del ' + str(inicio.day) + ' de ' + MESES_CHOICES[inicio.month - 1][1].capitalize() + ' del ' + str(inicio.year) + ' al ' + str(fin.day) + ' de ' + MESES_CHOICES[fin.month - 1][1].capitalize() + ' del ' + str(fin.year)

    return fecharango


def dictfetchall(cursor):
    "RETORNA TODAS LOS CAMPOS DL CURSOR QUE SEAN DISTINTO"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def lista_mejores_promedio_beca(periodoactual, periodoanterior=None, limit=10, filter_malla=None):
    from sga.models import Matricula, Malla, AsignaturaMalla, Inscripcion, MateriaAsignada, BecaPersona
    mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
    mids = Matricula.objects.filter(nivel__periodo=periodoactual, retiradomatricula=False, status=True,
                                    matriculagruposocioeconomico__tipomatricula=1,
                                    inscripcion__inscripcionnivel__nivel__orden__gt=1)
    mids = mids.values_list('inscripcion__inscripcionmalla__malla_id', flat=True).exclude(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles).distinct()
    mallas = Malla.objects.filter(pk__in=mids)
    if filter_malla:
        mallas = mallas.filter(pk=filter_malla.id)
    # mallas = mallas.filter(pk=208)
    # mallas = mallas.filter(pk=9)
    mejores_promedio_inscripciones = []
    mallas_promedio_inscripciones = []
    for malla in mallas:
        count_mejor = 0
        matriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                              inscripcion__inscripcionmalla__malla=malla,
                                              inscripcion__perfilusuario__inscripcion__isnull=False,
                                              inscripcion__perfilusuario__inscripcion__activo=True,
                                              retiradomatricula=False, status=True,
                                              matriculagruposocioeconomico__tipomatricula=1,
                                              inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                              )
        if periodoanterior:
            matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                          inscripcion__inscripcionmalla__malla=malla,
                                                          inscripcion__perfilusuario__inscripcion__isnull=False,
                                                          inscripcion__perfilusuario__inscripcion__activo=True,
                                                          retiradomatricula=False, status=True,
                                                          matriculagruposocioeconomico__tipomatricula=2)
            matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
            matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
        matriculas = matriculas.order_by('-inscripcion__promedio').distinct()
        for matricula in matriculas:
            if count_mejor == limit:
                break
            arrpromedio = []
            inscripcion = matricula.inscripcion
            materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
            records = inscripcion.recordacademico_set.filter(status=True)
            historicos = inscripcion.historicorecordacademico_set.filter(status=True)
            """para conciderar el mejor promedio debe estar matriculado regular y no tener registro de reprobados en el record academico"""
            if materias.count() > 0 and records.filter(aprobada=False).count() == 0 and historicos.filter(aprobada=False).count() == 0:
                if count_mejor < limit:
                    count_mejor += 1
                    mejores_promedio_inscripciones.append(inscripcion.id)
                    arrpromedio.append(inscripcion.id)
                    print(u"Mejor Promedio -- Carrera: %s, estudiante: %s" % (malla.carrera, inscripcion.persona))
        mallas_promedio_inscripciones.append({'malla': malla.id, 'inscripciones': arrpromedio})
    return {"lista": mejores_promedio_inscripciones, "mallas": mallas_promedio_inscripciones}


def lista_discapacitado_beca(periodoactual, periodoanterior=None, promedio=None, excludes=[]):
    from sga.models import Matricula, Raza, MateriaAsignada, BecaPersona, Inscripcion, Malla
    promedio = promedio if promedio else 0
    mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
    razas = Raza.objects.filter(status=True)
    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s'%(periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)

    matriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                          inscripcion__perfilusuario__inscripcion__isnull=False,
                                          inscripcion__perfilusuario__inscripcion__activo=True,
                                          retiradomatricula=False, status=True,
                                          matriculagruposocioeconomico__tipomatricula=1,
                                          inscripcion__promedio__gte=promedio,
                                          inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                          inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                          inscripcion__persona__deportistapersona__isnull=True,
                                          inscripcion__persona__pais_id=1,
                                          inscripcion__persona__migrantepersona__isnull=True,
                                          inscripcion__persona__perfilinscripcion__raza__in=razas.exclude(pk__in=[1, 2, 5]),
                                          nivelmalla__in=nivelesmallapermitidos
                                          )
    matriculas = matriculas.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    matricula_exclusion_1 = matriculas.annotate(total_ingles=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles, nivel__periodo=periodoactual, status=True)),
                                                total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_ingles'))
    matricula_exclusion_2 = matriculas.annotate(total_titulacion=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__nivel__nivellibrecoordinacion__coordinacion__id=12, nivel__periodo=periodoactual, status=True)),
                                                total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_titulacion'))
    matriculas = matriculas.exclude(id__in=matricula_exclusion_1.values_list('id', flat=True))
    matriculas = matriculas.exclude(id__in=matricula_exclusion_2.values_list('id', flat=True))
    if periodoanterior:
        matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                      inscripcion__perfilusuario__inscripcion__isnull=False,
                                                      inscripcion__perfilusuario__inscripcion__activo=True,
                                                      retiradomatricula=False, status=True,
                                                      matriculagruposocioeconomico__tipomatricula=2,
                                                      materiaasignada__estado_id__in=[2, 3, 4])
        matriculasanterior = matriculasanterior.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
        matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
    matriculas = matriculas.exclude(inscripcion_id__in=excludes).distinct()

    matriculas_segundonivel = matriculas.filter(inscripcion__inscripcionnivel__nivel__orden__gt=1)
    discapacitados = []
    for matricula in matriculas_segundonivel:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists() and inscripcion.persona.es_ecuatoriano():
                materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                isBecado = True
                suma = 0
                promedio_anterior = 0
                if materias.count() > 0:
                    asignatura = MateriaAsignada.objects.filter(status=True,
                                                                matricula__inscripcion=matricula.inscripcion,
                                                                matricula__nivel__periodo=periodoanterior,
                                                                materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                    total = asignatura.count()
                    for m in asignatura:
                        suma += m.notafinal
                        if m.estado.id != 1:
                            isBecado = False
                            break
                    if suma > 0 and isBecado:
                        promedio_anterior = round(suma / total, 2)
                        if promedio_anterior < 75:
                            isBecado = False
                else:
                    isBecado = False
                if isBecado:
                    discapacitados.append(inscripcion.id)
                    print(u"Discapacitado -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))

    matriculas_primernivel = matriculas.filter(inscripcion__inscripcionnivel__nivel__orden=1)
    if periodoanterior:
        matriculas_primernivel = matriculas_primernivel.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        matriculas_primernivel = matriculas_primernivel.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
    for matricula in matriculas_primernivel:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
            isBecado = True
            if materias.count() > 0:
                asignatura = MateriaAsignada.objects.filter(status=True,
                                                            matricula__inscripcion=matricula.inscripcion,
                                                            matricula__nivel__periodo=periodoanterior,
                                                            materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])

                for m in asignatura:
                    if m.estado.id != 1:
                        isBecado = False
                        break
            if isBecado:
                discapacitados.append(inscripcion.id)
    return discapacitados


def lista_deportista_beca(periodoactual, periodoanterior=None, promedio=None, excludes=[]):
    from sga.models import Matricula, Raza, MateriaAsignada, BecaPersona, Inscripcion
    promedio = promedio if promedio else 0
    razas = Raza.objects.filter(status=True)
    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s' % (periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)
    matriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                          inscripcion__perfilusuario__inscripcion__isnull=False,
                                          inscripcion__perfilusuario__inscripcion__activo=True,
                                          retiradomatricula=False, status=True,
                                          matriculagruposocioeconomico__tipomatricula=1,
                                          inscripcion__promedio__gte=promedio,
                                          inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                          inscripcion__persona__deportistapersona__isnull=False,
                                          inscripcion__persona__deportistapersona__status=True,
                                          inscripcion__persona__deportistapersona__vigente=1,
                                          inscripcion__persona__pais_id=1,
                                          inscripcion__persona__migrantepersona__isnull=True,
                                          inscripcion__persona__perfilinscripcion__raza__in=razas.exclude(pk__in=[1, 2, 5]))
    matriculas = matriculas.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    if periodoanterior:
        matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                      inscripcion__perfilusuario__inscripcion__isnull=False,
                                                      inscripcion__perfilusuario__inscripcion__activo=True,
                                                      retiradomatricula=False, status=True,
                                                      matriculagruposocioeconomico__tipomatricula=2,
                                                      materiaasignada__estado_id__in=[2, 3, 4])
        matriculasanterior = matriculasanterior.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
        matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
    matriculas = matriculas.exclude(inscripcion_id__in=excludes, inscripcion__persona__perfilinscripcion__tienediscapacidad=True, inscripcion__persona__perfilinscripcion__verificadiscapacidad=True, ).distinct()
    deportistas = []
    for matricula in matriculas:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                isBecado = True
                suma = 0
                promedio_anterior = 0
                if materias.count() > 0:
                    asignatura = MateriaAsignada.objects.filter(status=True,
                                                                matricula__inscripcion=matricula.inscripcion,
                                                                matricula__nivel__periodo=periodoanterior,
                                                                materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                    total = asignatura.count()
                    for m in asignatura:
                        suma += m.notafinal
                        if m.estado.id != 1:
                            isBecado = False
                            break
                    if suma > 0 and isBecado:
                        promedio_anterior = round(suma / total, 2)
                        if promedio_anterior < 70:
                            isBecado = False
                else:
                    isBecado = False

                if isBecado:
                    deportistas.append(inscripcion.id)
                    print(u"Deportista -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))

    return deportistas


def lista_migrante_exterior_beca(periodoactual, periodoanterior=None, promedio=None, excludes=[]):
    from sga.models import Matricula, Raza, BecaPersona, MateriaAsignada, Inscripcion
    promedio = promedio if promedio else 0
    razas = Raza.objects.filter(status=True)
    inscripciones_ids = []
    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s'%(periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)
    exteriores = Matricula.objects.filter(~Q(inscripcion__persona__pais_id=1),
                                          nivel__periodo=periodoactual,
                                          inscripcion__perfilusuario__inscripcion__isnull=False,
                                          inscripcion__perfilusuario__inscripcion__activo=True,
                                          retiradomatricula=False, status=True,
                                          matriculagruposocioeconomico__tipomatricula=1,
                                          inscripcion__promedio__gte=promedio,
                                          inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                          inscripcion__persona__migrantepersona__isnull=True,
                                          inscripcion__persona__pais__isnull=False,
                                          inscripcion__persona__paisnacimiento_id=1,
                                          inscripcion__persona__perfilinscripcion__raza__in=razas.exclude(pk__in=[1, 2, 5]))
    exteriores = exteriores.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    migrantes = Matricula.objects.filter(nivel__periodo=periodoactual,
                                         inscripcion__perfilusuario__inscripcion__isnull=False,
                                         inscripcion__perfilusuario__inscripcion__activo=True,
                                         retiradomatricula=False, status=True,
                                         matriculagruposocioeconomico__tipomatricula=1,
                                         inscripcion__promedio__gte=promedio,
                                         inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                         inscripcion__persona__pais_id=1,
                                         inscripcion__persona__paisnacimiento_id=1,
                                         inscripcion__persona__migrantepersona__isnull=False,
                                         inscripcion__persona__perfilinscripcion__raza__in=razas.exclude(pk__in=[1, 2, 5]))
    migrantes = migrantes.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))

    if periodoanterior:
        matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                      inscripcion__perfilusuario__inscripcion__isnull=False,
                                                      inscripcion__perfilusuario__inscripcion__activo=True,
                                                      retiradomatricula=False, status=True,
                                                      matriculagruposocioeconomico__tipomatricula=2,
                                                      materiaasignada__estado_id__in=[2, 3, 4])
        matriculasanterior = matriculasanterior.filter(nivelmalla__orden__lt=7).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
        exteriores = exteriores.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        exteriores = exteriores.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
        migrantes = migrantes.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        migrantes = migrantes.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
    exteriores = exteriores.exclude(inscripcion_id__in=excludes,
                                    inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                    inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                    inscripcion__persona__deportistapersona__isnull=False,
                                    inscripcion__persona__deportistapersona__status=True,
                                    inscripcion__persona__deportistapersona__vigente=1).distinct()
    inscripciones_ids = []
    for matricula in exteriores:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                if materias.count() > 0:
                    isBecado = True
                    suma = 0
                    promedio_anterior = 0
                    if materias.count() > 0:
                        asignatura = MateriaAsignada.objects.filter(status=True,
                                                                    matricula__inscripcion=matricula.inscripcion,
                                                                    matricula__nivel__periodo=periodoanterior,
                                                                    materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                        total = asignatura.count()
                        for m in asignatura:
                            suma += m.notafinal
                            if m.estado.id != 1:
                                isBecado = False
                                break
                        if suma > 0 and isBecado:
                            promedio_anterior = round(suma / total, 2)
                            if promedio_anterior < 85:
                                isBecado = False
                    else:
                        isBecado = False

                    if isBecado:
                        inscripciones_ids.append(inscripcion.id)
                        print(u"Ecuatoriano en el exterior -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))
    migrantes = migrantes.exclude(inscripcion_id__in=excludes,
                                  inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                  inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                  inscripcion__persona__deportistapersona__isnull=False,
                                  inscripcion__persona__deportistapersona__status=True,
                                  inscripcion__persona__deportistapersona__vigente=1).distinct()

    for matricula in migrantes:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                if materias.count() > 0:
                    isBecado = True
                    suma = 0
                    promedio_anterior = 0
                    if materias.count() > 0:
                        asignatura = MateriaAsignada.objects.filter(status=True,
                                                                    matricula__inscripcion=matricula.inscripcion,
                                                                    matricula__nivel__periodo=periodoanterior,
                                                                    materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                        for m in asignatura:
                            if m.notafinal < 85 or m.estado.id != 1:
                                isBecado = False
                                break
                    else:
                        isBecado = False

                    if isBecado:
                        inscripciones_ids.append(inscripcion.id)
                        print(u"Migrante retornado -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))

    return inscripciones_ids


def lista_etnia_beca(periodoactual, periodoanterior=None, promedio=None, excludes=[]):
    from sga.models import Matricula, Raza, BecaPersona, MateriaAsignada, Inscripcion
    promedio = promedio if promedio else 0
    razas = Raza.objects.filter(status=True)
    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s'%(periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)
    matriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                          inscripcion__perfilusuario__inscripcion__isnull=False,
                                          inscripcion__perfilusuario__inscripcion__activo=True,
                                          retiradomatricula=False, status=True,
                                          matriculagruposocioeconomico__tipomatricula=1,
                                          inscripcion__promedio__gte=promedio,
                                          inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                          inscripcion__persona__pais_id=1,
                                          inscripcion__persona__perfilinscripcion__raza__in=razas.filter(pk__in=[1, 2, 5]))
    matriculas = matriculas.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    if periodoanterior:
        matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                      inscripcion__perfilusuario__inscripcion__isnull=False,
                                                      inscripcion__perfilusuario__inscripcion__activo=True,
                                                      retiradomatricula=False, status=True,
                                                      matriculagruposocioeconomico__tipomatricula=2,
                                                      materiaasignada__estado_id__in=[2, 3, 4])
        matriculasanterior = matriculasanterior.filter(nivelmalla__orden__lt=7).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
        matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))

    matriculas = matriculas.exclude(inscripcion_id__in=excludes,
                                    inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                    inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                    inscripcion__persona__deportistapersona__isnull=False,
                                    inscripcion__persona__deportistapersona__status=True,
                                    inscripcion__persona__deportistapersona__vigente=1).distinct()

    if not promedio:
        promedio = round(null_to_numeric(matriculas.aggregate(prom=Avg('inscripcion__promedio'))['prom']), 2)
        matriculas = matriculas.filter(inscripcion__promedio__gte=promedio)
    etnias = []
    for matricula in matriculas:
        inscripcion = matricula.inscripcion
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                if materias.count() > 0:
                    isBecado = True
                    suma = 0
                    promedio_anterior = 0
                    if materias.count() > 0:
                        asignatura = MateriaAsignada.objects.filter(status=True,
                                                                    matricula__inscripcion=matricula.inscripcion,
                                                                    matricula__nivel__periodo=periodoanterior,
                                                                    materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                        total = asignatura.count()
                        for m in asignatura:
                            suma += m.notafinal
                            if m.estado.id != 1:
                                isBecado = False
                                break
                        if suma > 0 and isBecado:
                            promedio_anterior = round(suma / total, 2)
                            if promedio_anterior < 85:
                                isBecado = False
                    else:
                        isBecado = False

                    if isBecado:
                        etnias.append(inscripcion.id)
                        print(u"Etnia -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))
    return etnias


def lista_gruposocioeconomico_beca(periodoactual, periodoanterior=None, tipogrupo_id=None, excludes=[], limit=20, filter_malla=None):
    from sga.models import Matricula, Malla, BecaPersona, MateriaAsignada, Inscripcion, Periodo,PreInscripcionBeca
    mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
    mids = Matricula.objects.filter(nivel__periodo=periodoactual, retiradomatricula=False, status=True,
                                    matriculagruposocioeconomico__tipomatricula=1,
                                    inscripcion__inscripcionnivel__nivel__orden__gt=1)

    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s'%(periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)
    mids = mids.filter(nivelmalla__in=nivelesmallapermitidos).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    if tipogrupo_id:
        mids = mids.filter(inscripcion__persona__fichasocioeconomicainec__grupoeconomico_id=tipogrupo_id)
    mids = mids.values_list('inscripcion__inscripcionmalla__malla_id', flat=True).distinct()#.exclude(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles)

    # matriculas a excluir que solo vieron materias de ingles en el actual periodo
    matricula_exclusion = mids.annotate(total_ingles=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles, nivel__periodo=periodoactual, status=True)),
                                        total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_ingles'))
    mallas = Malla.objects.filter(pk__in=mids).exclude(id__in=mallas_ingles)
    if filter_malla:
        mallas = mallas.filter(pk=filter_malla.id)
    # mallas = mallas.filter(pk=208)
    #mallas = mallas.filter(pk=213)
    inscripciones_ids = []
    if periodoanterior:
        matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                      inscripcion__perfilusuario__inscripcion__isnull=False,
                                                      inscripcion__perfilusuario__inscripcion__activo=True,
                                                      retiradomatricula=False, status=True,
                                                      matriculagruposocioeconomico__tipomatricula=2,
                                                      materiaasignada__estado_id__in=[2, 3, 4])
        matriculasanterior = matriculasanterior.filter(nivelmalla__orden__gt=1, nivelmalla__orden__lt=7).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    for malla in mallas:
        count_mejor = 0
        matriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                              inscripcion__inscripcionmalla__malla=malla,
                                              inscripcion__perfilusuario__inscripcion__isnull=False,
                                              inscripcion__perfilusuario__inscripcion__activo=True,
                                              retiradomatricula=False, status=True,
                                              matriculagruposocioeconomico__tipomatricula=1,
                                              inscripcion__inscripcionnivel__nivel__orden__gt=1).exclude(id__in=matricula_exclusion.filter(inscripcion__carrera_id=malla.carrera_id).values_list('id', flat=True))
        matriculas = matriculas.filter(nivelmalla__orden__gt=1, nivelmalla__orden__lt=7).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
        if periodoanterior:
            matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
        if tipogrupo_id:
            matriculas = matriculas.filter(inscripcion__persona__fichasocioeconomicainec__grupoeconomico_id=tipogrupo_id)
        matriculas = matriculas.exclude(inscripcion_id__in=excludes).order_by('-inscripcion__promedio').distinct()
        matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))

        # periodos = ()
        # if periodoactual:
        #     periodos = Periodo.objects.filter(pk__in=[periodoactual.pk]).values_list('id', flat=True)
        periodos = Periodo.objects.exclude(pk=periodoanterior.id).values_list('id', flat=True)
        matriculas_prebecas = [] #[[matricula, matricula.inscripcion.calcular_promedio_beca(periodos)] for matricula in matriculas]
        for matricula in matriculas:
            promediototal = matricula.inscripcion.calcular_promedio_beca(periodos)
            if promediototal > 70:
                matriculas_prebecas.append([matricula, promediototal])

        matriculas_prebecas = sorted(matriculas_prebecas, key=itemgetter(1), reverse=True)

        for row in matriculas_prebecas:
            matricula = row[0]
            if limit > 0:
                if count_mejor == limit:
                    break
            inscripcion = matricula.inscripcion
            if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
                inscripcion.__setattr__('promediototal', row[1])
                if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                    materias = matricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                    if materias.count() > 0:
                        isBecado = True
                        if materias.count() > 0:
                            asignatura = MateriaAsignada.objects.filter(status=True,
                                                                        matricula__inscripcion=matricula.inscripcion,
                                                                        matricula__nivel__periodo=periodoanterior,
                                                                        materiaasignadaretiro__isnull=True).exclude(materia__asignaturamalla__malla_id__in=[353, 22])
                            for m in asignatura:
                                if m.estado.id != 1:
                                    isBecado = False
                                    break
                        else:
                            isBecado = False

                        if isBecado:
                            if limit > 0:
                                if count_mejor < limit:
                                    count_mejor += 1
                                    inscripciones_ids.append(inscripcion)
                                    print(u"Grupo vulnerable (%s) -- Carrera: %s, estudiante: %s Promedio: %s" % (tipogrupo_id, inscripcion.carrera, inscripcion.persona, inscripcion.promediototal))
                            else:
                                inscripciones_ids.append(inscripcion)
                                print(u"Grupo vulnerable (%s) -- Carrera: %s, estudiante: %s Promedio: %s" % (tipogrupo_id, inscripcion.carrera, inscripcion.persona, inscripcion.promediototal))
        # if limit:
        #     inscripciones_ids.extend(list(matriculas.values_list('inscripcion_id', flat=True).distinct()[:limit]))
        # else:
        #     inscripciones_ids.extend(list(matriculas.values_list('inscripcion_id', flat=True).distinct()))

    return inscripciones_ids


def lista_mejores_promedio_beca_v2(periodo, limit=10, fmalla=None):
    from sga.models import Matricula, Malla
    malla_ids = Matricula.objects.filter(nivel__periodo=periodo, status=True).values_list('inscripcion__inscripcionmalla__malla_id', flat=True).distinct()
    mallas = Malla.objects.filter(pk__in=malla_ids)
    if fmalla:
        mallas = mallas.filter(pk=fmalla.id)
    mejores_promedios_inscripciones = []
    promdio_inscripciones = []
    mallas_promedios_inscripciones = []
    for malla in mallas:
        ARR_mallas_promedios_inscripciones = []
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    lista.inscripcion_id,
                    lista.promedio
                FROM
                    listado_inscripcion_promedio AS lista
                    INNER JOIN "public".sga_matricula AS matricula ON lista.inscripcion_id = matricula.inscripcion_id
                    AND matricula."id" IN (
                        SELECT DISTINCT
                            mateasi.matricula_id
                        FROM
                            "public".sga_materiaasignada AS mateasi
                        INNER JOIN "public".sga_materia AS ma ON ma."id" = mateasi.materia_id
                        INNER JOIN "public".sga_nivel AS ni ON ni."id" = ma.nivel_id
                        INNER JOIN "public".sga_asignaturamalla AS asima ON asima."id" = ma.asignaturamalla_id
                        WHERE
                            ni.periodo_id = %s
                            AND asima.malla_id NOT IN (353, 22)
                    )
                WHERE
                    lista.periodo_id = %s
                AND lista.nivelmalla_id > 1
                AND matricula.tipomatricula_id = 1
                AND malla_id = %s
                ORDER BY
                    lista.promedio DESC
                LIMIT %s"""
            cursor.execute(sql % (periodo.id, periodo.id, malla.id, limit))
            rows = dictfetchall(cursor)
            for row in rows:
                mejores_promedios_inscripciones.append(row['inscripcion_id'])
            num_matriculados = Matricula.objects.filter(nivel__periodo=periodo, status=True, inscripcion__inscripcionmalla__malla=malla).count()
            sql = """
                SELECT
                    lista.inscripcion_id,
                    lista.promedio
                FROM
                    listado_inscripcion_promedio AS lista
                    INNER JOIN "public".sga_matricula AS matricula ON lista.inscripcion_id = matricula.inscripcion_id
                    AND matricula."id" IN (
                        SELECT DISTINCT
                            mateasi.matricula_id
                        FROM
                            "public".sga_materiaasignada AS mateasi
                        INNER JOIN "public".sga_materia AS ma ON ma."id" = mateasi.materia_id
                        INNER JOIN "public".sga_nivel AS ni ON ni."id" = ma.nivel_id
                        INNER JOIN "public".sga_asignaturamalla AS asima ON asima."id" = ma.asignaturamalla_id
                        WHERE
                            ni.periodo_id = %s
                            AND asima.malla_id NOT IN (353, 22)
                    )
                WHERE
                    lista.periodo_id = %s
                AND lista.nivelmalla_id > 1
                AND malla_id = %s
                AND matricula.tipomatricula_id = 1
                ORDER BY
                    lista.promedio DESC
                LIMIT %s"""
            cursor.execute(sql % (periodo.id, periodo.id, malla.id, num_matriculados))
            rows = dictfetchall(cursor)
            for row in rows:
                promdio_inscripciones.append(row['inscripcion_id'])
                ARR_mallas_promedios_inscripciones.append(row['inscripcion_id'])
            mallas_promedios_inscripciones.append({'malla_id': malla.id, 'inscripciones': ARR_mallas_promedios_inscripciones})
    return {"listamejores": mejores_promedios_inscripciones, "mallas": mallas_promedios_inscripciones, "lista": promdio_inscripciones}


def lista_discapacitado_beca_v2(periodo, promedio=None, mejorespromedio=[]):
    discapacidad = 0
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promedio = promedio if promedio else 0
    inscripciones_ids = []
    with connection.cursor() as cursor:
        sql = """
                SELECT
                    lista_gse.inscripcion_id AS inscripcion_id
                FROM
                    listado_inscripcion_gruposocioeconomico AS lista_gse
                INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                WHERE
                    lista_gse.semestre_id > 1
                    AND mgse.tipomatricula = 1
                    AND lista_gse.promedio >= %s
                    AND lista_gse.tienediscapacidad = 'SI'
                    AND lista_gse.deportista = 'NO'
                    AND lista_gse.exterior = 'NO'
                    AND lista_gse.migrante = 'NO'
                    AND lista_gse.periodo_id = %s
                    AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                    AND lista_gse.inscripcion_id NOT IN (%s)"""
        cursor.execute(sql % (promedio, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
        rows = dictfetchall(cursor)
        for row in rows:
            inscripciones_ids.append(row['inscripcion_id'])
    return {"lista": inscripciones_ids}


def lista_deportista_beca_v2(periodo, promedio=None, mejorespromedio=[]):
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promedio = promedio if promedio else 0
    inscripciones_ids = []
    with connection.cursor() as cursor:
        sql = """
                SELECT
                    lista_gse.inscripcion_id AS inscripcion_id
                FROM
                    listado_inscripcion_gruposocioeconomico AS lista_gse
                    INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                WHERE
                    lista_gse.semestre_id > 1
                    AND mgse.tipomatricula = 1
                    AND lista_gse.promedio >= %s
                    AND lista_gse.tienediscapacidad = 'NO'
                    AND lista_gse.deportista = 'SI'
                    AND lista_gse.exterior = 'NO'
                    AND lista_gse.migrante = 'NO'
                    AND lista_gse.periodo_id = %s
                    AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                    AND lista_gse.inscripcion_id NOT IN (%s)"""
        cursor.execute(sql % (promedio, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
        rows = dictfetchall(cursor)
        for row in rows:
            inscripciones_ids.append(row['inscripcion_id'])
    return {"lista": inscripciones_ids}


def lista_migrante_beca_v2(periodo, promedio=None, mejorespromedio=[]):
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promedio = promedio if promedio else 0
    inscripciones_ids = []
    with connection.cursor() as cursor:
        sql = """
                SELECT
                    lista_gse.inscripcion_id AS inscripcion_id
                FROM
                    listado_inscripcion_gruposocioeconomico AS lista_gse
                    INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                WHERE
                    lista_gse.semestre_id > 1
                    AND mgse.tipomatricula = 1
                    AND lista_gse.promedio >= %s
                    AND lista_gse.tienediscapacidad = 'NO'
                    AND lista_gse.deportista = 'NO'
                    AND lista_gse.exterior = 'NO'
                    AND lista_gse.migrante = 'SI'
                    AND lista_gse.periodo_id = %s
                    AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                    AND lista_gse.inscripcion_id NOT IN (%s)"""
        cursor.execute(sql % (promedio, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
        rows = dictfetchall(cursor)
        for row in rows:
            inscripciones_ids.append(row['inscripcion_id'])
    return {"lista": inscripciones_ids}


def lista_exterior_beca_v2(periodo, promedio=None, mejorespromedio=[]):
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promedio = promedio if promedio else 0
    inscripciones_ids = []
    with connection.cursor() as cursor:
        sql = """
                SELECT
                    lista_gse.inscripcion_id AS inscripcion_id
                FROM
                    listado_inscripcion_gruposocioeconomico AS lista_gse
                    INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                WHERE
                    lista_gse.semestre_id > 1
                    AND mgse.tipomatricula = 1
                    AND lista_gse.promedio >= %s
                    AND lista_gse.tienediscapacidad = 'NO'
                    AND lista_gse.deportista = 'NO'
                    AND lista_gse.exterior = 'SI'
                    AND lista_gse.migrante = 'NO'
                    AND lista_gse.periodo_id = %s
                    AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                    AND lista_gse.inscripcion_id NOT IN (%s)"""
        cursor.execute(sql % (promedio, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
        rows = dictfetchall(cursor)
        for row in rows:
            inscripciones_ids.append(row['inscripcion_id'])
    return {"lista": inscripciones_ids}


def lista_etnia_beca_v2(periodo, promedio=None, mejorespromedio=[]):
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promedio = promedio if promedio else 0
    inscripciones_ids = []
    if not promedio:
        with connection.cursor() as cursor:
            sql = """
                            SELECT
                                round(AVG(lista_gse.promedio), 0) AS promedio
                            FROM
                                listado_inscripcion_gruposocioeconomico AS lista_gse
                                INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                            WHERE
                                lista_gse.semestre_id > 1
                                AND mgse.tipomatricula = 1
                                AND lista_gse.tienediscapacidad = 'NO'
                                AND lista_gse.deportista = 'NO'
                                AND lista_gse.exterior = 'NO'
                                AND lista_gse.migrante = 'NO'
                                AND lista_gse.periodo_id = %s
                                AND lista_gse.etnia_id IN (1, 2, 5) 
                                AND lista_gse.inscripcion_id NOT IN (%s)"""
            cursor.execute(sql % (periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
            row = cursor.fetchone()
            promedio = row[0]

    with connection.cursor() as cursor:
        sql = """
                SELECT
                    lista_gse.inscripcion_id AS inscripcion_id
                FROM
                    listado_inscripcion_gruposocioeconomico AS lista_gse
                    INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                WHERE
                    lista_gse.semestre_id > 1
                    AND mgse.tipomatricula = 1
                    AND lista_gse.promedio >= %s
                    AND lista_gse.tienediscapacidad = 'NO'
                    AND lista_gse.deportista = 'NO'
                    AND lista_gse.exterior = 'NO'
                    AND lista_gse.migrante = 'NO'
                    AND lista_gse.periodo_id = %s
                    AND lista_gse.etnia_id IN (1, 2, 5) 
                    AND lista_gse.inscripcion_id NOT IN (%s)"""
        cursor.execute(sql % (promedio, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
        rows = dictfetchall(cursor)
        for row in rows:
            inscripciones_ids.append(row['inscripcion_id'])
    return {"lista": inscripciones_ids}


def lista_gruposocioeconomico_beca_v2(periodo, tipogrupo_id=[], promedio=None, aplicapromedio=False, mejorespromedio=[], aplicamejoresmalla=False, limit=20):
    promedios_inscripciones = mejorespromedio
    if not mejorespromedio:
        results = lista_mejores_promedio_beca_v2(periodo)
        promedios_inscripciones = results['listamejores']
    promediogrupo = promedio if promedio else 0
    if aplicapromedio:
        with connection.cursor() as cursor:
            sql = """
                    SELECT
                        round(AVG(lista_gse.promedio), 0) AS promedio
                    FROM
                        listado_inscripcion_gruposocioeconomico AS lista_gse
                        INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                    WHERE
                        lista_gse.semestre_id > 1
                        AND mgse.tipomatricula = 1
                        AND lista_gse.gse_id IN (%s)
                        AND lista_gse.tienediscapacidad = 'NO'
                        AND lista_gse.deportista = 'NO'
                        AND lista_gse.exterior = 'NO'
                        AND lista_gse.migrante = 'NO'
                        AND lista_gse.periodo_id = %s
                        AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                        AND lista_gse.inscripcion_id NOT IN (%s)"""
            cursor.execute(sql % ((",".join([str(x) for x in tipogrupo_id])), periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
            row = cursor.fetchone()
            promediogrupo = row[0]

    inscripciones_ids = []
    if not aplicamejoresmalla:
        with connection.cursor() as cursor:
            sql = """
                    SELECT
                        lista_gse.inscripcion_id AS inscripcion_id
                    FROM
                        listado_inscripcion_gruposocioeconomico AS lista_gse
                        INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                    WHERE
                        lista_gse.semestre_id > 1
                        AND mgse.tipomatricula = 1
                        AND lista_gse.gse_id IN (%s)
                        AND lista_gse.promedio >= %s
                        AND lista_gse.tienediscapacidad = 'NO'
                        AND lista_gse.deportista = 'NO'
                        AND lista_gse.exterior = 'NO'
                        AND lista_gse.migrante = 'NO'
                        AND lista_gse.periodo_id = %s
                        AND lista_gse.etnia_id NOT IN (1, 2, 5) 
                        AND lista_gse.inscripcion_id NOT IN (%s)"""
            cursor.execute(sql % ((",".join([str(x) for x in tipogrupo_id])), promediogrupo, periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
            rows = dictfetchall(cursor)
            for row in rows:
                inscripciones_ids.append(row['inscripcion_id'])
    else:
        # mallas_grupo = []
        with connection.cursor() as cursor:
            sql = """
                    SELECT
                        lista_gse.malla_id AS malla_id
                    FROM
                        listado_inscripcion_gruposocioeconomico AS lista_gse
                        INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                    WHERE
                        lista_gse.semestre_id > 1
                        AND mgse.tipomatricula = 1
                        AND lista_gse.gse_id IN (%s)
                        AND lista_gse.tienediscapacidad = 'NO'
                        AND lista_gse.deportista = 'NO'
                        AND lista_gse.exterior = 'NO'
                        AND lista_gse.migrante = 'NO'
                        AND lista_gse.periodo_id = %s
                        AND lista_gse.etnia_id NOT IN (1, 2, 5)
                        AND lista_gse.inscripcion_id NOT IN (%s)
                    GROUP BY
                        lista_gse.malla_id"""
            cursor.execute(sql % ((",".join([str(x) for x in tipogrupo_id])), periodo.id, (",".join([str(x) for x in promedios_inscripciones]))))
            rows = dictfetchall(cursor)
            for row in rows:
                # mallas_grupo.append(row['malla_id'])
                with connection.cursor() as cursor1:
                    sql1 = """
                            SELECT
                                lista_gse.inscripcion_id
                            FROM
                                listado_inscripcion_gruposocioeconomico AS lista_gse
                                INNER JOIN sga_matriculagruposocioeconomico AS mgse ON mgse.matricula_id = lista_gse.matricula_id
                            WHERE
                                lista_gse.semestre_id > 1
                                AND mgse.tipomatricula = 1
                                AND lista_gse.gse_id IN (%s)
                                AND lista_gse.tienediscapacidad = 'NO'
                                AND lista_gse.deportista = 'NO'
                                AND lista_gse.exterior = 'NO'
                                AND lista_gse.migrante = 'NO'
                                AND lista_gse.periodo_id = %s
                                AND lista_gse.etnia_id NOT IN (1, 2, 5)
                                AND lista_gse.malla_id = %s
                                AND lista_gse.inscripcion_id NOT IN (%s)
                            ORDER BY
                                lista_gse.promedio DESC
                            LIMIT %s"""
                    cursor1.execute(sql1 % ((",".join([str(x) for x in tipogrupo_id])), periodo.id, row['malla_id'], (",".join([str(x) for x in promedios_inscripciones])), limit))
                    rows1 = dictfetchall(cursor1)
                    for row1 in rows1:
                        inscripciones_ids.append(row1['inscripcion_id'])
    return {"lista": inscripciones_ids}


def notificacion(titulo, cuerpo, destinatario, departamento, url, object_id, prioridad, app_label, modelo, request):
    from sga.models import Notificacion
    from django.contrib.contenttypes.models import ContentType
    notificacion = Notificacion(titulo=(titulo[:300]),
                                cuerpo=cuerpo,
                                destinatario=destinatario,
                                # departamento=departamento,
                                url=url,
                                content_type=ContentType.objects.get(app_label=modelo._meta.app_label, model=modelo._meta.model_name),
                                object_id=object_id,
                                prioridad=prioridad,
                                app_label=app_label,
                                fecha_hora_visible=datetime.now() + timedelta(days=3)
                                )
    if request:
        notificacion.save(request)
    else:
        notificacion.save()

def notificacion2(titulo, cuerpo, destinatario, departamento, url, object_id, prioridad, app_label, modelo):
    from sga.models import Notificacion
    from django.contrib.contenttypes.models import ContentType

    notificacion = Notificacion(titulo=titulo,
                                cuerpo=cuerpo,
                                destinatario=destinatario,
                                # departamento=departamento,
                                url=url,
                                content_type=ContentType.objects.get(app_label=modelo._meta.app_label, model=modelo._meta.model_name),
                                object_id=object_id,
                                prioridad=prioridad,
                                app_label=app_label,
                                fecha_hora_visible=datetime.now() + timedelta(days=3)
                                )
    notificacion.save()

def notificacion3(titulo, cuerpo, destinatario, departamento, url, object_id, prioridad, app_label, modelo, perfil, request):
    from sga.models import Notificacion
    from django.contrib.contenttypes.models import ContentType

    notificacion = Notificacion(titulo=titulo,
                                cuerpo=cuerpo,
                                destinatario=destinatario,
                                perfil=perfil,
                                # departamento=departamento,
                                url=url,
                                content_type=ContentType.objects.get(app_label=modelo._meta.app_label, model=modelo._meta.model_name),
                                object_id=object_id,
                                prioridad=prioridad,
                                app_label=app_label,
                                fecha_hora_visible=datetime.now() + timedelta(days=1)
                                )
    notificacion.save(request)

def notificacion4(titulo, cuerpo, destinatario, departamento, url, object_id, prioridad, app_label, modelo, perfil):
    from sga.models import Notificacion
    from django.contrib.contenttypes.models import ContentType

    notificacion = Notificacion(titulo=titulo,
                                cuerpo=cuerpo,
                                destinatario=destinatario,
                                # departamento=departamento,
                                perfil=perfil,
                                url=url,
                                content_type=ContentType.objects.get(app_label=modelo._meta.app_label, model=modelo._meta.model_name),
                                object_id=object_id,
                                prioridad=prioridad,
                                app_label=app_label,
                                fecha_hora_visible=datetime.now() + timedelta(days=1)
                                )
    notificacion.save()

def notificacion_masivo_grupo(titulo, cuerpo, usergroups, url, object_id, prioridad, app_label, modelo):
    from sga.models import Notificacion, Persona
    from django.contrib.contenttypes.models import ContentType
    userslist = []

    if type(usergroups) is int:
        usergroups = [usergroups]

    if Group.objects.values('id').filter(id__in=usergroups).exists():
        userslist = Group.objects.filter(id__in=usergroups).first().user_set.values_list('id', flat=True)

    destinatarios = Persona.objects.filter(usuario_id__in=userslist, status=True)

    for destinatario in destinatarios:
        notificacion = Notificacion(titulo=titulo,
                                    cuerpo=cuerpo,
                                    destinatario=destinatario,
                                    url=url,
                                    content_type=ContentType.objects.get(app_label=modelo._meta.app_label, model=modelo._meta.model_name),
                                    object_id=object_id,
                                    prioridad=prioridad,
                                    app_label=app_label,
                                    fecha_hora_visible=datetime.now() + timedelta(days=1))
        notificacion.save()


def subreport_directory_path(instance, filename):
    return 'reportes/subreportes/{0}/{1}'.format(instance.reporte.id, filename)


def ingreso_total_hogar_rangos(sbu):
    from sagest.models import AnioEjercicio
    anio = datetime.now().year
    if AnioEjercicio.objects.filter(anioejercicio=anio).exists():
        anioejercicio = AnioEjercicio.objects.filter(anioejercicio=anio)[0]
        sbuanio = anioejercicio.sbu
        if sbu <= sbuanio:
            return "RANGO1"
        if sbu <= (sbuanio * 2):
            return "RANGO2"
        if sbu <= (sbuanio * 3):
            return "RANGO3"
        if sbu <= (sbuanio * 4):
            return "RANGO4"
        if sbu <= (sbuanio * 5):
            return "RANGO5"
        if sbu <= (sbuanio * 6):
            return "RANGO6"
        if sbu <= (sbuanio * 7):
            return "RANGO7"
        if sbu <= (sbuanio * 8):
            return "RANGO8"
        if sbu <= (sbuanio * 9):
            return "RANGO9"
        else:
            return "RANGO10"
    return "NO REGISTRA"


def export_to_excel(columnas=[], queryset=None, filename="reporte_excel", nombre_hoja="Hoja 1"):
    import xlwt
    from django.http import HttpResponse
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="{}.xls"'.format(filename)
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(nombre_hoja)
    # columnas2 = list(columnas)
    # columnas2.sort(key=len, reverse=True)
    # col_width = 256 * len(columnas2[0])
    # Sheet header, first row
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    columns = columnas

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    rows = queryset
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)
    wb.save(response)
    return response


def convertir_string_ip(ips):
    import ipaddress
    ip = None
    try:
        ip = ipaddress.ip_address(ips)
    except Exception as ex:
        ip = None
    return ip


def convertir_ip_string(ip):
    return str(ip)


def get_director_vinculacion():
    # from sagest.models import Departamento
    # departamentogestion = Departamento.objects.filter(pk=111)
    # responsablevinculacion = departamentogestion.first().responsable if departamentogestion.exists() else None
    from sga.models import ConfiguracionFirmaPracticasPreprofesionales
    responsablevinculacion = ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, activo=True, esprincipal=True).first() if ConfiguracionFirmaPracticasPreprofesionales.objects.filter(status=True, activo=True, esprincipal=True).exists() else None
    return responsablevinculacion


def convertir_lista(query):
    return list(query)


def adicionar_nota_complexivo(idgraduado, nota, item, fecha, request=None):
    from sga.models import ExamenComlexivoGraduados
    if ExamenComlexivoGraduados.objects.filter(graduado_id=idgraduado, itemexamencomplexivo=item).exists():
        itendetalle = ExamenComlexivoGraduados.objects.get(graduado_id=idgraduado, itemexamencomplexivo=item)
        itendetalle.examen = nota
        itendetalle.ponderacion = null_to_decimal((nota / 2), 2)
        itendetalle.fecha = fecha
        if request:
            log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "edit")
    else:
        itendetalle = ExamenComlexivoGraduados(graduado_id=idgraduado,
                                               itemexamencomplexivo=item,
                                               examen=nota,
                                               ponderacion=null_to_decimal((nota / 2), 2),
                                               fecha=fecha
                                               )
        if request:
            log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "add")
    if request:
        itendetalle.save(request)
    else:
        itendetalle.save()


def calculo_desviacion_estandar_becas(periodo, li=1.0, lf=1.0, nv=0.1):
    from sga.models import Materia, Malla
    materias = Materia.objects.values_list('asignaturamalla__malla_id').filter(nivel__periodo=periodo)
    mallas = Malla.objects.filter(pk__in=materias).exclude(pk__in=[22, 353])[::5]
    aData = []
    for malla in mallas:
        cursor = connection.cursor()
        sqlnum = """select num_estudiantes_x_carrera_x_periodo_all (%s, 1, %s) """ % (
            periodo.id, malla.id)
        cursor.execute(sqlnum)
        num_estudiantes_carrera = cursor.fetchone()[0]
        # print(num_estudiantes_carrera)
        cursor = connection.cursor()
        sqlpromedio = """select promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodo.id, malla.id)
        cursor.execute(sqlpromedio)
        promedio = float(cursor.fetchone()[0])
        # print(promedio)
        sqldesviacion = """select stddev_promedio_carrera_x_periodo_all (%s, 1, %s) """ % (
            periodo.id, malla.id)
        cursor.execute(sqldesviacion)
        desviacion = float(cursor.fetchone()[0])
        # print(desviacion)
        # while li <= lf:
        v1 = null_to_numeric(li * desviacion, 2)
        v2 = null_to_numeric(((li * desviacion) + promedio), 2)
        sqlnum_estudiantes = """select num_estudiantes_x_carrera_x_periodo_promedio_all (%s, 1, %s, %s) """ % (
            periodo.id, malla.id, v2)
        cursor.execute(sqlnum_estudiantes)
        v3 = cursor.fetchone()[0]
        # print(v3)
        try:
            v4 = null_to_numeric(((v3 / num_estudiantes_carrera) * 100), 2)
        except ZeroDivisionError:
            v4 = 0

        aData.append({
            "malla": malla,
            "num": null_to_numeric(li, 2),
            "desviacion": v1,
            "nota_ref": v2,
            "num_becados": v3,
            "porcentaje_becados": v4})
        # li += nv
    return aData


def listado_becados_por_desviacionestandar_todas_carrera(periodo):
    from sga.models import Materia, Malla, Inscripcion
    try:
        li = 1.0
        materias = Materia.objects.values_list('asignaturamalla__malla_id').filter(nivel__periodo=periodo)
        mallas = Malla.objects.filter(pk__in=materias,
                                      carrera__inscripcion__isnull=False,
                                      carrera__inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                      carrera__coordinacion__in=[1, 2, 3, 4, 5]).exclude(pk__in=[22, 353]).distinct()
        listadomallas = []
        ID_MEJOR_PROMEDIO = 17
        totalgeneral = 0
        inscripcionestotales = Inscripcion.objects.none()
        for malla in mallas:
            cursor = connection.cursor()
            sqlnum = """select num_estudiantes_x_carrera_x_periodo_all (%s, 1, %s) """ % (
                periodo.id, malla.id)
            cursor.execute(sqlnum)
            num_estudiantes_carrera = cursor.fetchone()[0]
            # print(num_estudiantes_carrera)
            cursor = connection.cursor()
            sqlpromedio = """select promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodo.id, malla.id)
            cursor.execute(sqlpromedio)
            promedio = float(cursor.fetchone()[0])
            # print(promedio)
            sqldesviacion = """select stddev_promedio_carrera_x_periodo_all (%s, 1, %s) """ % (
                periodo.id, malla.id)
            cursor.execute(sqldesviacion)
            desviacion = float(cursor.fetchone()[0])
            # print(desviacion)
            # while li <= lf:
            v1 = null_to_numeric(li * desviacion, 2)
            v2 = null_to_numeric(((li * desviacion) + promedio), 2)
            sqlnum_estudiantes = """select num_estudiantes_x_carrera_x_periodo_promedio_all (%s, 1, %s, %s) """ % (
                periodo.id, malla.id, v2)
            cursor.execute(sqlnum_estudiantes)
            v3 = cursor.fetchone()[0]
            totalgeneral += v3
            try:
                v4 = null_to_numeric(((v3 / num_estudiantes_carrera) * 100), 2)
            except ZeroDivisionError:
                v4 = 0
            # inscripcion_ids = Matricula.objects.values_list('inscripcion_id', flat=False).filter(
            #     nivel__periodo=periodo, inscripcion__carrera=malla.carrera, status=True, retiradomatricula=False)
            # aData = []

            # inscripciones = Inscripcion.objects.filter(pk__in=inscripcion_ids, promedio__gte=v2).order_by('promedio')

            inscripciones = Inscripcion.objects.filter(promedio__gte=v2,
                                                       matricula__nivel__periodo_id=periodo.id,
                                                       carrera_id=malla.carrera.id,
                                                       matricula__status=True,
                                                       matricula__retiradomatricula=False).order_by('promedio').distinct()
            inscripcionestotales = inscripcionestotales | inscripciones
            # for inscripcion in inscripciones:
            #     promedio = null_to_decimal(RecordAcademico.objects.filter(status=True, inscripcion=inscripcion,
            #                                                               asignaturamalla_id__in=asignaturamalla_ids).aggregate(
            #         promedio=Avg('nota'))['promedio'], 2)
            #     promedio2 = inscripcion.promedio
            #     if promedio >= v2:
            #         nivel = inscripcion.inscripcionnivel_set.filter(status=True).first()
            #         periodo_id = TarjetaRegistroAcademico.objects.values_list('periodo_id', flat=True).filter(
            #             inscripcion=inscripcion).order_by('periodo__inicio')
            #         periodoinicio = None
            #         if periodo_id.exists():
            #             periodoinicio = Periodo.objects.get(pk=periodo_id.first())
            #
            #         # aData.append({"inscripcion_id": inscripcion.id,
            #         #               "inscripcion": inscripcion.persona,
            #         #               "promedio": promedio,
            #         #               "nivel": nivel,
            #         #               "periodo": periodoinicio.nombre if periodoinicio else "S/R"})
            #         aData.append(inscripcion.id)
            # ord_aData = sorted(aData, key=lambda promedio: promedio['promedio'], reverse=True)

        return inscripcionestotales
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        return None


def listado_becados_por_desviacionestandar_todas_carreranew(periodoactual, periodoanterior=None, limit=None, filter_malla=None, excludes=[]):
    #limite de promedio
    from sga.models import Materia, Malla, Inscripcion, Matricula
    try:
        li = 1.0
        periodo = periodoanterior if periodoanterior else periodoactual

        mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
        materias = Materia.objects.values_list('asignaturamalla__malla_id').filter(nivel__periodo=periodoactual)

        mallas = Malla.objects.filter(pk__in=materias,
                                      carrera__inscripcion__isnull=False,
                                      carrera__inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                      carrera__coordinacion__in=[1, 2, 3, 4, 5]).exclude(pk__in=mallas_ingles).distinct()

        totalgeneral = 0
        inscripcionestotales = []#Inscripcion.objects.none()
        for malla in mallas:
            inscripciones_segundo_nivel = Inscripcion.objects.filter(
                inscripcionmalla__malla_id=malla.id,
                matricula__nivel__periodo_id=periodoanterior.id,
                inscripcionnivel__nivel__orden__gt=1)
            if inscripciones_segundo_nivel:
                cursor = connection.cursor()
                sqlnum = """select num_estudiantes_x_carrera_x_periodo_all (%s, 1, %s) """ % (
                    periodo.id, malla.id)
                cursor.execute(sqlnum)
                num_estudiantes_carrera = cursor.fetchone()[0]
                # print(num_estudiantes_carrera)
                cursor = connection.cursor()
                sqlpromedio = """select promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodo.id, malla.id)
                cursor.execute(sqlpromedio)
                promedio = float(cursor.fetchone()[0])
                # print(promedio)
                sqldesviacion = """select stddev_promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodo.id, malla.id)
                cursor.execute(sqldesviacion)
                desviacion = float(cursor.fetchone()[0])
                # print(desviacion)
                # while li <= lf:
                v1 = null_to_numeric(li * desviacion, 2)
                v2 = null_to_numeric(((li * desviacion) + promedio), 2)
                sqlnum_estudiantes = """select num_estudiantes_x_carrera_x_periodo_promedio_all (%s, 1, %s, %s) """ % (
                    periodo.id, malla.id, v2)
                cursor.execute(sqlnum_estudiantes)
                v3 = cursor.fetchone()[0]
                totalgeneral += v3
                try:
                    v4 = null_to_numeric(((v3 / num_estudiantes_carrera) * 100), 2)
                except ZeroDivisionError:
                    v4 = 0

                inscripciones = Inscripcion.objects.filter(
                    recordacademico__status=True,
                    recordacademico__asignaturamalla__malla_id=malla.id,
                    matricula__nivel__periodo_id=periodo.id,
                    carrera_id=malla.carrera.id,
                    matricula__matriculagruposocioeconomico__tipomatricula=1,
                    inscripcionnivel__nivel__orden__gt=1,
                    matricula__status=True,
                    matricula__retiradomatricula=False).distinct().annotate(promediototal=Avg('recordacademico__nota')).filter(promediototal__gte=v2).order_by('-promediototal')

                matriculados = Matricula.objects.filter(inscripcion__id__in=inscripciones.values_list('pk', flat=True),
                                                        inscripcion__inscripcionmalla__malla=malla,
                                                        nivel__periodo_id=periodoactual.id,
                                                        retiradomatricula=False, status=True,
                                                        matriculagruposocioeconomico__tipomatricula=1).distinct().order_by("inscripcion__persona").values_list('inscripcion_id', flat=True)

                inscripciones = inscripciones.filter(pk__in=matriculados).order_by('-promediototal')
                if limit:
                    inscripciones = inscripciones[:limit] if inscripciones.count() > limit else list(inscripciones)
                else:
                    inscripciones = list(inscripciones)
                inscripcionestotales.extend(inscripciones)
        #inscripcionestotales = inscripcionestotales.exclude(pk__in=excludes) if excludes else inscripcionestotales
        # print(len(inscripcionestotales))
        return inscripcionestotales
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        return None


def listado_incripciones_reconocimiento_academico(periodoactual, periodoanterior=None, excludes=[]):
    from sga.models import Inscripcion
    periodo = periodoanterior if periodoanterior else periodoactual
    inscripciones = Inscripcion.objects.filter(
        persona__titulacion__detalletitulacionbachiller__reconocimientoacademico__isnull=False,
        persona__titulacion__detalletitulacionbachiller__anioinicioperiodograduacion__isnull=False,
        persona__titulacion__detalletitulacionbachiller__aniofinperiodograduacion__isnull=False,
        persona__titulacion__detalletitulacionbachiller__calificacion__gt=0,
        persona__titulacion__detalletitulacionbachiller__status=True,
        status=True,
        matricula__estado_matricula__in=[2, 3],
        matricula__nivel__periodo_id=periodoanterior,
        matricula__nivelmalla_id=1)
    inscripciones = inscripciones.exclude(pk__in=excludes) if excludes else inscripciones
    listado_inscripciones = []
    for inscripcion in inscripciones:
        if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            listado_inscripciones.append(inscripcion)
            print(u"Reconocimiemto Academico Primer Nivel: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))

    return listado_inscripciones


def listado_becados_por_desviacionestandar_todas_carreramejorado(periodoactual, periodoanterior=None, limit=10, filter_malla=None, excludes=[]):
    #limite de promedio
    from operator import itemgetter, attrgetter
    from django.db import connection, connections
    from sga.models import Materia, Malla, Inscripcion, Periodo, Matricula
    try:
        li = 1.0
        periodo = periodoanterior if periodoanterior else periodoactual

        # mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
        # materias = Materia.objects.values_list('asignaturamalla__malla_id').filter(nivel__periodo=periodoactual)
        #
        # mallas = Malla.objects.filter(pk__in=materias,
        #                               carrera__inscripcion__isnull=False,
        #                               carrera__inscripcion__inscripcionnivel__nivel__orden__gt=1,
        #                               carrera__coordinacion__in=[1, 2, 3, 4, 5]).exclude(pk__in=mallas_ingles).distinct()

        mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
        mids = Matricula.objects.filter(nivel__periodo=periodoactual, retiradomatricula=False, status=True,
                                        matriculagruposocioeconomico__tipomatricula=1,
                                        inscripcion__inscripcionnivel__nivel__orden__gt=1)
        mids = mids.values_list('inscripcion__inscripcionmalla__malla_id', flat=True).distinct()
        #matriculas a excluir que solo vieron materias de ingles en el actual periodo
        matricula_exclusion = mids.annotate(total_ingles=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles, nivel__periodo=periodoactual, status=True)),
                                            total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_ingles'))
        mallas = Malla.objects.filter(pk__in=mids).exclude(id__in=mallas_ingles)

        totalgeneral = 0
        inscripcionestotales = []#Inscripcion.objects.none()
        for malla in mallas:
            inscripciones_segundo_nivel = Inscripcion.objects.filter(
                inscripcionmalla__malla_id=malla.id,
                matricula__nivel__periodo_id=periodoanterior.id,
                inscripcionnivel__nivel__orden__gt=1)
            if inscripciones_segundo_nivel:
                cursor = connection.cursor()
                sqlnum = """select num_estudiantes_x_carrera_x_periodo_all (%s, 1, %s) """ % (
                    periodo.id, malla.id)
                cursor.execute(sqlnum)
                num_estudiantes_carrera = cursor.fetchone()[0]
                # print(num_estudiantes_carrera)
                cursor = connection.cursor()
                sqlpromedio = """select promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodoanterior.id, malla.id)
                cursor.execute(sqlpromedio)
                promedio = float(cursor.fetchone()[0])
                # print(promedio)
                sqldesviacion = """select stddev_promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodoanterior.id, malla.id)
                cursor.execute(sqldesviacion)
                desviacion = float(cursor.fetchone()[0])

                # print(desviacion)
                # while li <= lf:
                v1 = null_to_numeric(li * desviacion, 2)
                v2 = null_to_numeric(((li * desviacion) + promedio), 2)
                sqlnum_estudiantes = """select num_estudiantes_x_carrera_x_periodo_promedio_all (%s, 1, %s, %s) """ % (
                    periodoanterior.id, malla.id, v2)
                cursor.execute(sqlnum_estudiantes)
                v3 = cursor.fetchone()[0]
                totalgeneral += v3
                try:
                    v4 = null_to_numeric(((v3 / num_estudiantes_carrera) * 100), 2)
                except ZeroDivisionError:
                    v4 = 0

                inscripciones = Inscripcion.objects.filter(
                    perfilusuario__inscripcion__isnull=False,
                    perfilusuario__inscripcion__activo=True,
                    inscripcionmalla__malla_id=malla.id,
                    matricula__nivel__periodo_id=periodoactual.id,
                    carrera_id=malla.carrera.id,
                    matricula__matriculagruposocioeconomico__tipomatricula=1,
                    inscripcionnivel__nivel__orden__gt=1,
                    matricula__status=True,
                    status=True,
                    matricula__retiradomatricula=False).exclude(persona_id__in=[inscripcion.persona.id for inscripcion in inscripcionestotales])
                inscripciones = inscripciones.exclude(id__in=matricula_exclusion.filter(inscripcion__carrera_id=malla.carrera_id).values_list('inscripcion_id', flat=True))
                periodos = Periodo.objects.exclude(pk=periodoanterior.id).values_list('id', flat=True)
                incripciones_mallas = []
                for inscripcion in inscripciones:
                    #regular anterior periodo
                    if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
                        regular_periodoanterior = inscripcion.matricula_set.filter(
                            nivel__periodo_id=periodoanterior.id,
                            matriculagruposocioeconomico__tipomatricula=1,
                            status=True,
                            retiradomatricula=False).values('id')

                        if regular_periodoanterior:
                            promedioperiodoanterior = inscripcion.calcular_promedio_beca(periodos)
                            if promedioperiodoanterior >= v2:
                                inscripcion.__setattr__('promediototal', promedioperiodoanterior)
                                inscripcion.__setattr__('nota_referencial', v2)
                                inscripcion.__setattr__('desviacion_estandar', desviacion)
                                inscripcion.__setattr__('promedio_carrera', promedio)
                                incripciones_mallas.append(inscripcion)
                inscripciones = sorted(incripciones_mallas, key=lambda inscripcion: inscripcion.promediototal, reverse=True)

                if limit:
                    inscripciones = inscripciones[:limit] if len(inscripciones) > limit else inscripciones
                #presentar inscripciones
                inscripcionestotales.extend(inscripciones)

                for inscripcion in inscripciones:
                    print(u"Alto Rendimiento -- Carrera: %s, estudiante: %s, promedio: %s, nota_referencial: %s" % (inscripcion.carrera, inscripcion.persona, inscripcion.promediototal, inscripcion.nota_referencial))

        #inscripcionestotales = inscripcionestotales.exclude(pk__in=excludes) if excludes else inscripcionestotales
        #print(len(inscripcionestotales))
        return inscripcionestotales
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        return None


def lista_discapacitado_beca2(periodoactual, periodoanterior=None, promedio=None, excludes=[]):
    from sga.models import Raza, BecaPersona, Inscripcion
    promedio = promedio if promedio else 0
    razas = Raza.objects.filter(status=True)
    inscripciones = Inscripcion.objects.filter(matricula__nivel__periodo=periodoanterior,
                                               perfilusuario__inscripcion__isnull=False,
                                               perfilusuario__inscripcion__activo=True,
                                               matricula__retiradomatricula=False, status=True,
                                               matricula__matriculagruposocioeconomico__tipomatricula=1,
                                               inscripcionnivel__nivel__orden__gt=1,
                                               persona__perfilinscripcion__tienediscapacidad=True,
                                               persona__perfilinscripcion__verificadiscapacidad=True,
                                               persona__deportistapersona__isnull=True,
                                               persona__pais_id=1,
                                               persona__migrantepersona__isnull=True,
                                               persona__perfilinscripcion__raza__in=razas.exclude(pk__in=[1, 2, 5])).annotate(promediototal=Avg('recordacademico__nota')).exclude(promediototal__lt=75)
    inscripciones.exclude(persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
    inscripciones.exclude(pk__in=excludes)
    #print(u"Discapacitado -- Carrera: %s, estudiante: %s" % (inscripcion.carrera, inscripcion.persona))
    return list(inscripciones)


def rangomeses(fechaInicio, fechaFin):
    from dateutil import rrule
    tiempo = rrule.rrule(rrule.MONTHLY, dtstart=fechaInicio, until=fechaFin)
    return tiempo.count()


def validar_persona_convarias_inscripciones(inscripcion, periodoanterior, periodoactual):
    from sga.models import Inscripcion, PreInscripcionBeca, Matricula
    matriculas_extras = Matricula.objects.filter(inscripcion__persona_id=inscripcion.persona.id,
                                                inscripcion__activo=True,
                                                nivel__periodo=periodoactual,
                                                matriculagruposocioeconomico__tipomatricula=1,
                                                status=True,
                                                matricula__retiradomatricula=False,
                                                retiradomatricula=False).exclude(inscripcion__coordinacion_id=9)


    if matriculas_extras.count() > 1:
        preinscripcion_periodoanterior = PreInscripcionBeca.objects.filter(periodo=periodoanterior,
                                                                           inscripcion_id__in=matriculas_extras.values_list(
                                                                               'inscripcion_id', flat=True)).first()
        menor_nivel = 0
        if not preinscripcion_periodoanterior:
            for i, matricula in enumerate(matriculas_extras):
                insc = matricula.inscripcion
                minivel = insc.mi_nivel().nivel.orden
                menor_nivel = minivel if i == 0 else menor_nivel
                inscripcion = insc if minivel <= menor_nivel else inscripcion
    return inscripcion


def asignar_orden_portipo_beca(becatipo_id, periodo, filtro_carrera=[]):
    from sga.models import PreInscripcionBeca
    preinscripciones = PreInscripcionBeca.objects.filter(becatipo_id=becatipo_id, periodo=periodo)
    if filtro_carrera:
        preinscripciones = preinscripciones.filter(inscripcion__carrera_id__in=filtro_carrera)
    preinscripciones = preinscripciones.order_by('inscripcion__carrera__nombre', '-promedio')

    aux_carrera = 0
    contador = 1
    print("NUMERO DE ORDEN ESTUDIANTES DE BECAS POR PROMEDIO")
    for i, preinscripcion in enumerate(preinscripciones):
        aux_carrera = preinscripcion.inscripcion.carrera_id if i == 0 else aux_carrera
        if aux_carrera != preinscripcion.inscripcion.carrera_id:
            contador = 1
            aux_carrera = preinscripcion.inscripcion.carrera_id
        preinscripcion.orden = contador
        preinscripcion.save()
        print(f'{i+1}.- {preinscripcion} carrerrera {preinscripcion.inscripcion.carrera} su orden es {contador}')
        contador += 1


def logvisita(request, urlPath, gruposid):
    try:
        if variable_valor('GUARDAR_MODULOS_VISITADOS'):
            from sga.models import VisitaModulos, Modulo
            modulo_ = Modulo.objects.filter(modulogrupo__grupos__id__in=gruposid, url=urlPath, activo=True).values('url', 'nombre', 'id').first()
            if modulo_:
                if not VisitaModulos.objects.values('id').filter(fecha_creacion__date=datetime.now().date(), usuario_creacion=request.user, modulo=modulo_['id'], modulo_url=modulo_['url'] ,modulo_nombre=modulo_['nombre']).exists():
                    visita_ = VisitaModulos(modulo_id=modulo_['id'], modulo_url=modulo_['url'] ,modulo_nombre=modulo_['nombre'])
                    visita_.save(request)
    except Exception as ex:
        pass


def lista_mejores_promedio_beca_v3(periodoactual, periodoanterior=None, limit=10, filter_malla=None):
    from sga.models import Matricula, Malla, AsignaturaMalla, Inscripcion, MateriaAsignada, BecaPersona, Periodo
    from django.db.models import OuterRef, Exists, Q, F
    mallas_ingles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
    periodobeca = periodoactual.becaperiodo_set.filter(status=True).first()
    if periodobeca is None:
        raise NameError(u'No se a configurado periodo beca para el periodo %s'% (periodoactual))
    nivelesmallapermitidos = periodobeca.nivelesmalla.filter(status=True).values_list('id', flat=True)
    if not nivelesmallapermitidos.exists():
        raise NameError(u'No existe niveles permitidos para el periodo %s' % periodobeca)
    subquery = Matricula.objects.filter(nivel__periodo_id=153,
                                        retiradomatricula=False,
                                        matriculagruposocioeconomico__status=True,
                                        matriculagruposocioeconomico__tipomatricula=1,
                                        inscripcion_id=OuterRef('id'))

    inscripciones = Inscripcion.objects.filter(
                                               perfilusuario__status=True,
                                               perfilusuario__inscripcionprincipal=True,
                                               perfilusuario__visible=True,
                                               matricula__nivel__periodo_id=177,
                                               matricula__status=True,
                                               matricula__retiradomatricula=False,
                                               matricula__matriculagruposocioeconomico__status=True,
                                               matricula__matriculagruposocioeconomico__tipomatricula=1,
                                               inscripcionmalla__malla__vigente=True,
                                               inscripcionmalla__status=True,
                                               coordinacion_id__in=[1, 2, 3, 4, 5],
                                               ).filter(Q(Q(persona__paisnacimiento_id=1) |
                                                          Q(persona__pais_id=1, persona__nacionalidad=('ECUATORIANA', 'ECUATORIANO'))
                                                          )
                                               ).annotate(regular_periodoanterior=Exists(subquery)).filter(regular_periodoanterior=True)



    eMatriculas = Matricula.objects.filter(nivel__periodo=periodoactual,
                                           retiradomatricula=False,
                                           status=True,
                                           matriculagruposocioeconomico__tipomatricula=1,
                                           inscripcion__inscripcionnivel__nivel__orden__gt=1,
                                           nivelmalla__in=nivelesmallapermitidos,
                                           #nivelmalla__orden__gt=1,
                                           #nivelmalla__orden__lt=7
                                           )
    eMatriculas = eMatriculas.exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
    eMatriculas_1 = eMatriculas.annotate(total_ingles=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles, nivel__periodo=periodoactual, status=True)),
                                         total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_ingles'))
    eMatriculas_2 = eMatriculas.annotate(total_titulacion=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(materiaasignada__materia__nivel__nivellibrecoordinacion__coordinacion__id=12, nivel__periodo=periodoactual, status=True)),
                                         total_general=Count('materiaasignada__materia__asignaturamalla__malla_id', filter=Q(nivel__periodo=periodoactual, status=True))).filter(total_general=F('total_titulacion'))
    eMatriculas = eMatriculas.exclude(id__in=eMatriculas_1.values_list('id', flat=True))
    eMatriculas = eMatriculas.exclude(id__in=eMatriculas_2.values_list('id', flat=True))
    # idsm = eMatriculas.values_list('inscripcion__inscripcionmalla__malla_id', flat=True)
    eMallas = Malla.objects.filter(pk__in=eMatriculas.values('inscripcion__inscripcionmalla__malla__id'), vigente=True).exclude(id__in=mallas_ingles)
    if filter_malla:
        eMallas = eMallas.filter(pk=filter_malla.id)
    # mallas = mallas.filter(pk=208)
    #mallas = mallas.filter(pk=218)
    mejores_promedio_inscripciones = []
    mallas_promedio_inscripciones = []
    li = 1.0
    periodos = Periodo.objects.exclude(pk=periodoanterior.id).values_list('id', flat=True)
    totalgeneral = 0
    inscripcionestotales = []
    try:
        for malla in eMallas:
            count_mejor = 0
            cursor = connection.cursor()
            sqlnum = """select num_estudiantes_x_carrera_x_periodo_all (%s, 1, %s) """ % (periodoanterior.id, malla.id)
            cursor.execute(sqlnum)
            num_estudiantes_carrera = cursor.fetchone()[0]
            # print(num_estudiantes_carrera)
            cursor = connection.cursor()
            sqlpromedio = """select promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodoanterior.id, malla.id)
            cursor.execute(sqlpromedio)
            volor_promedio = cursor.fetchone()[0]
            promedio = float(volor_promedio if not volor_promedio is None else 0)
            # print(promedio)
            sqldesviacion = """select stddev_promedio_carrera_x_periodo_all (%s, 1, %s) """ % (periodoanterior.id, malla.id)
            cursor.execute(sqldesviacion)
            valor_desvi = cursor.fetchone()[0]
            desviacion = float(valor_desvi if not valor_desvi is None else 0)

            # print(desviacion)
            # while li <= lf:
            v1 = null_to_numeric(li * desviacion, 2)
            v2 = null_to_numeric(((li * desviacion) + promedio), 2)
            sqlnum_estudiantes = """select num_estudiantes_x_carrera_x_periodo_promedio_all (%s, 1, %s, %s) """ % (periodoanterior.id, malla.id, v2)
            cursor.execute(sqlnum_estudiantes)
            v3 = cursor.fetchone()[0]
            totalgeneral += v3

            try:
                v4 = null_to_numeric(((v3 / num_estudiantes_carrera) * 100), 2)
            except ZeroDivisionError:
                v4 = 0
            matriculas = eMatriculas.filter(inscripcion__inscripcionmalla__malla=malla)
            matriculas = matriculas.exclude(inscripcion__persona_id__in=[inscripcion.persona.id for inscripcion in inscripcionestotales])
            if periodoanterior:
                matriculasanterior = Matricula.objects.filter(nivel__periodo=periodoanterior,
                                                              inscripcion__inscripcionmalla__malla=malla,
                                                              inscripcion__perfilusuario__inscripcion__isnull=False,
                                                              inscripcion__perfilusuario__inscripcion__activo=True,
                                                              retiradomatricula=False, status=True,
                                                              matriculagruposocioeconomico__tipomatricula=2)
                matriculasanterior = matriculasanterior.filter(nivelmalla__orden__gt=1, nivelmalla__orden__lt=7).exclude(Q(inscripcion__graduado__status=True) | Q(inscripcion__graduado__status=True))
                matriculas = matriculas.exclude(inscripcion_id__in=matriculasanterior.values_list('inscripcion_id', flat=True))
                matriculas = matriculas.exclude(inscripcion__persona_id__in=BecaPersona.objects.values_list('persona_id', flat=True).filter(institucion_id=2, status=True))
            matriculas = matriculas.order_by('-inscripcion__promedio').distinct()
            incripciones_mallas = []
            if promedio > 70 and desviacion > 0:
                for matricula in matriculas:
                    inscripcion = matricula.inscripcion
                    if inscripcion.persona.es_ecuatoriano() and not inscripcion.tiene_materias_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not inscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
                        promedioperiodoanterior = inscripcion.calcular_promedio_beca(periodos)
                        if promedioperiodoanterior >= v2:
                            inscripcion.__setattr__('promediototal', promedioperiodoanterior)
                            inscripcion.__setattr__('nota_referencial', v2)
                            inscripcion.__setattr__('desviacion_estandar', desviacion)
                            inscripcion.__setattr__('promedio_carrera', promedio)
                            incripciones_mallas.append(inscripcion)
                inscripciones = sorted(incripciones_mallas, key=lambda inscripcion: inscripcion.promediototal, reverse=True)
                if limit:
                    inscripciones = inscripciones[:limit] if len(inscripciones) > limit else inscripciones
                inscripcionestotales.extend(inscripciones)
                for inscripcion in inscripciones:
                    print(u"Alto Rendimiento -- Carrera: %s, estudiante: %s, promedio: %s, nota_referencial: %s" % (inscripcion.carrera, inscripcion.persona, inscripcion.promediototal, inscripcion.nota_referencial))
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
    return inscripcionestotales

def logiteraccion(mensaje, request, modelo, accion, persona_id, nombre=None, id_modelo=None,lista=[]):
    try:
        from gdocumental.models import LogIteraccion
        from django.contrib.contenttypes.models import ContentType
        if not id_modelo:
            id_modelo=modelo.id
        content_type=ContentType.objects.get_for_model(modelo)
        instancia=LogIteraccion(persona_id=persona_id,
                                nombre=nombre,
                                accion=accion,
                                mensaje_accion=mensaje,
                                object_id=id_modelo,
                                content_type=content_type)
        instancia.save(request)
        if lista:
            for l in lista:
                if type(l) is int:
                    instancia.personas_compartidas.add(l)
                else:
                    instancia.personas_compartidas.add(l[0])
            instancia.save(request)
    except Exception as ex:
        pass

def resetear_clave_edcon(persona):
    from sga.models import UsuarioLdap
    password = DEFAULT_PASSWORD
    reseteo_edcon = False
    if CLAVE_USUARIO_CEDULA:
        if not persona.usuario.is_superuser:
            if persona.cedula:
                password = persona.cedula.strip()
            elif persona.pasaporte:
                password = persona.pasaporte.strip()
            else:
                password = persona.ruc.strip()
            user = persona.usuario
            user.set_password(password)
            user.save()
            UsuarioLdap.objects.filter(usuario=user).delete()
            persona.cambiar_clave()
            if variable_valor('VALIDAR_LDAP'):
                validar_ldap_edcon(user.username, password, persona)
            reseteo_edcon = True
    return reseteo_edcon


def validar_ldap_edcon(usuario, clave, persona):
    from sga.models import UsuarioLdap
    if not UsuarioLdap.objects.filter(usuario_id=persona.usuario_id, status=True).exists():
        # if not UsuarioLdap.objects.filter(usuario_id=persona.usuario_id, status=True).exists():
        from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
        server = Server('10.142.0.39', port=389, get_info=ALL)
        conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
        usuario_aux = persona.emailinst.split('@')[0]
        busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
        if conn.search(busqueda, '(objectclass=person)'):
            # lo encontro
            conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
        else:
            # no lo encontro
            nombres = persona.nombres
            apellidos = persona.apellido1 + ' ' + persona.apellido2
            nombre_completo = nombres + apellidos
            mail = persona.emailinst
            conn.add(busqueda, ['inetOrgPerson'],
                     {'givenName': nombres, 'sn': apellidos, 'uid': usuario_aux, 'cn': nombre_completo, 'mail': mail,
                      'userPassword': clave})
        conn.unbind()
        usuarioldap = UsuarioLdap(usuario=persona.usuario)
        usuarioldap.save()
    # else:
    #     from ldap3 import Server, Connection, ALL, ObjectDef, AttrDef, Reader, Writer, MODIFY_REPLACE
    #     server = Server('10.142.0.39', port=389, get_info=ALL)
    #     conn = Connection(server, 'cn=admfeli,dc=uopenldap,dc=unemi,dc=edu,dc=ec', 'Op3nLd4p?F3l1p3*2021*Un3m1', auto_bind=True)
    #     usuario_aux = persona.emailinst.split('@')[0]
    #     busqueda = u"uid=%s,ou=People,dc=uopenldap,dc=unemi,dc=edu,dc=ec" % usuario_aux
    #     if conn.search(busqueda, '(objectclass=person)'):
    #         # lo encontro
    #         conn.modify(busqueda, {'userPassword': [(MODIFY_REPLACE, [clave])]})
    #     conn.unbind()


# Guardar en EPUNEMI los rubros migrados desde UNEMI 04/05/2023
def salvaRubrosEpunemiEdcon(model, action, qs_nuevo=None, qs_anterior=None):
    import json
    arr = []
    anterior = {}
    nuevo = {}
    if qs_anterior:
        anterior["fields"] = {}
        for x in qs_anterior:
            for k, v in x.items():
                anterior["fields"][k] = str(v)
        anterior["pk"] = qs_anterior[0]["id"]
        anterior["fields"]["__ff_detalle_ff__"] = "ANTERIOR"
        anterior["model"] = "sagest.rubro"
        arr.append(anterior)
    if qs_nuevo:
        nuevo["fields"] = {}
        for x in qs_nuevo:
            for k, v in x.items():
                nuevo["fields"][k] = str(v)
        nuevo["pk"] = qs_nuevo[0]["id"]
        nuevo["fields"]["__ff_detalle_ff__"] = "NUEVO"
        nuevo["model"] = "sagest.rubro"
        arr.append(nuevo)
    data_json = json.dumps(arr)
    # guardar en EPUNEMI el log del rubro migrado desde Unemi
    cursor = connections['epunemi'].cursor()
    sql = """ Insert Into sagest_logrubros (status, fecha_creacion, usuario_id, usuario_creacion_id, rubro_id, accion, datos_json)
        VALUES(TRUE, '/%s/', 1, 1, %s, '%s', '%s'); """ % (
        datetime.now(),
        model['id'],
        f'{action.upper()} MIGRADODEUNEMI',
        data_json)
    cursor.execute(sql)
    cursor.close()


def prueba_becas(periodo_actual=177, periodo_anterior=153):
    from django.db.models import OuterRef, Exists, Q, F, Count, Subquery, Avg, Sum
    from sga.models import Matricula, SacionEstudiante, RecordAcademico, AsignaturaMalla
    from sagest.models import Rubro
    mallas_ingles = [353, 22]
    subquery_matriculaanterior = Matricula.objects.filter(nivel__periodo_id=periodo_anterior,
                                                          retiradomatricula=False,
                                                          matriculagruposocioeconomico__status=True,
                                                          matriculagruposocioeconomico__tipomatricula=1,
                                                          inscripcion_id=OuterRef('inscripcion_id'))

    fechaactual = datetime.now().date()
    subquery_sancion_estudiante = SacionEstudiante.objects.filter(
        Q(inscripcion_id=OuterRef('inscripcion_id')) &
        Q(
            Q(fechadesde__gte=fechaactual, fechahasta__lte=fechaactual) |
            Q(indifinido=True)
          )
    )
    subquery_rubros_vencidos = Rubro.objects.filter(persona_id=OuterRef('inscripcion__persona_id'),
                                                    fechavence__lt=fechaactual,
                                                    cancelado=False, status=True)



    subquery_record_academico = RecordAcademico.objects.filter(
        inscripcion_id=OuterRef('inscripcion__id'),
        asignatura__asignaturamalla__malla_id=OuterRef('inscripcion__inscripcionmalla__malla_id'),
        asignatura__asignaturamalla__nivelmalla_id=OuterRef('nivelmallaanterior_id'),
        status=True,
        aprobada=True
    ).values('inscripcion_id')

    subquery_asignaturamalla = AsignaturaMalla.objects.filter(
        malla_id=OuterRef('inscripcion__inscripcionmalla__malla_id'),
        malla__status=True,
        nivelmalla_id=OuterRef('nivelmallaanterior_id'),
        status=True
    ).values('malla_id')

    matriculas = Matricula.objects.filter(
                                            inscripcion__perfilusuario__status=True,
                                            inscripcion__perfilusuario__inscripcionprincipal=True,
                                            inscripcion__perfilusuario__visible=True,
                                            nivel__periodo_id=periodo_actual,
                                            nivelmalla__orden__gte=2,
                                            status=True,
                                            retiradomatricula=False,
                                            matriculagruposocioeconomico__status=True,
                                            matriculagruposocioeconomico__tipomatricula=1,
                                            inscripcion__inscripcionmalla__malla__vigente=True,
                                            inscripcion__inscripcionmalla__status=True,
                                            inscripcion__coordinacion_id__in=[1, 2, 3, 4, 5],
                                               ).filter(Q(
                                                          Q(inscripcion__persona__paisnacimiento_id=1) |
                                                          Q(inscripcion__persona__pais_id=1)#, inscripcion__persona__nacionalidad=('ECUATORIANA', 'ECUATORIANO')
                                                          )
                                               ).annotate(
                                                 nivelmallaanterior_id=Subquery(subquery_matriculaanterior.values('nivelmalla_id')[:1])
                                                ).annotate(
                                                regular_periodoanterior=Exists(subquery_matriculaanterior),
                                                tiene_rubros_vencidos=Exists(subquery_rubros_vencidos),
                                                tiene_sancion=Exists(subquery_sancion_estudiante),
                                                #aprobo_todas_materias_anterior_periodo=Exists(subquery_matriculaanterior_aprobo_materias),
                                                total_ingles=Count('materiaasignada__materia__asignaturamalla__malla_id',
                                                                   filter=Q(
                                                                       materiaasignada__materia__asignaturamalla__malla_id__in=mallas_ingles,
                                                                       nivel__periodo_id=periodo_actual,
                                                                       materiaasignada__retiramateria=False,
                                                                       materiaasignada__status=True,
                                                                       status=True)),
                                                total_general=Count('materiaasignada__materia__asignaturamalla__malla_id',
                                                                    filter=Q(
                                                                        nivel__periodo=periodo_actual,
                                                                        materiaasignada__retiramateria=False,
                                                                        materiaasignada__status=True,
                                                                        status=True)),
                                                total_titulacion=Count('materiaasignada__materia__asignaturamalla__malla_id',
                                                                       filter=Q(
                                                                           materiaasignada__materia__nivel__nivellibrecoordinacion__coordinacion__id=12,
                                                                           materiaasignada__retiramateria=False,
                                                                           materiaasignada__status=True,
                                                                           nivel__periodo=periodo_actual, status=True)),
                                                #promedio_nivel_record=Subquery(subquery_record_academico.annotate(promedio_nivel=Avg('nota')).values('promedio_nivel')),
                                                #total_creditos_nivel_record=Subquery(subquery_record_academico.annotate(creditos_record_nivel=Sum('creditos')).values('creditos_record_nivel')),
                                                #total_cantidad_asignatura_nivel_record=Subquery(subquery_record_academico.annotate(cantidad_record_nivel=Count('id')).values('cantidad_record_nivel')),
                                                #total_creditos_nivelmalla=Subquery(subquery_asignaturamalla.annotate(creditos_nivelmalla=Sum('creditos')).values('creditos_nivelmalla')),
                                                #total_cantidad_nivelmalla=Subquery(subquery_asignaturamalla.annotate(cantidad_nivelmalla=Count('id')).values('cantidad_nivelmalla')),
                                               ).filter(
                                                    regular_periodoanterior=True,
                                                    tiene_sancion=False,
                                                    tiene_rubros_vencidos=False,
                                                    #total_cantidad_asignatura_nivel_record=F('total_cantidad_nivelmalla')
                                                    #aprobo_todas_materias_anterior_periodo=True
                                               ).exclude(Q(total_general=F('total_titulacion')) | Q(total_general=F('total_ingles'))).order_by('inscripcion__carrera__nombre')

    print(f"Cantidad: {matriculas.count()}\n")
    for mat in matriculas:
        print(f"{mat}") #{mat.promedio_nivel_record}, {mat.total_creditos_nivel_record}, {mat.total_creditos_nivelmalla}, {mat.total_cantidad_asignatura_nivel_record}, {mat.total_cantidad_nivelmalla}")


def no_laborable(fecha):
    from sga.models import DiasNoLaborable
    return True if DiasNoLaborable.objects.filter(fecha=fecha).exclude(periodo__isnull=False).exists() else False


class TruncMonth(Func):
    function = 'DATE_TRUNC'
    template = "%(function)s('month', %(expressions)s)"


def mesesmenoresandias(start_date, end_date):
    current_date = start_date
    months_less_than_10_days = []

    while current_date <= end_date:
        next_month = current_date.replace(day=28) + timedelta(days=4)
        days_in_month = (next_month - timedelta(days=next_month.day)).day

        if current_date == start_date:
            days_in_month -= start_date.day - 1

        if current_date.month == end_date.month:
            days_in_month = end_date.day

        if days_in_month < 10:
            months_less_than_10_days.append(current_date.month)

        current_date = next_month.replace(day=1)
    return months_less_than_10_days


def llenar_requisitostitulacion(materia, request):
    from sga.models import RequisitoTitulacionMalla
    from inno.models import RequisitoIngresoUnidadIntegracionCurricular, RequisitoMateriaUnidadIntegracionCurricular
    eMalla = materia.asignaturamalla.malla
    eRequisitosAsignaturamalla = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(asignaturamalla=materia.asignaturamalla, activo=True, status=True)
    eRequisitosTitulacionMalla = RequisitoTitulacionMalla.objects.filter(malla=eMalla, activo=True, status=True)
    for rmalla in eRequisitosTitulacionMalla:
        if not rmalla.requisito.id in materia.requisitomateriaunidadintegracioncurricular_set.values_list('requisito_id', flat=True).filter(status=True):
            requisitomateri = RequisitoMateriaUnidadIntegracionCurricular(materia=materia,
                                                                          requisito=rmalla.requisito,
                                                                          orden=rmalla.orden,
                                                                          activo=rmalla.activo,
                                                                          obligatorio=rmalla.obligatorio,
                                                                          titulacion=True)
            requisitomateri.save(request)
        else:
            requisitomateri = RequisitoMateriaUnidadIntegracionCurricular.objects.get(materia=materia, requisito=rmalla.requisito)
            requisitomateri.orden = rmalla.orden
            requisitomateri.activo = rmalla.activo
            requisitomateri.obligatorio = rmalla.obligatorio
            requisitomateri.titulacion = True
            requisitomateri.save(request)

    if not eRequisitosAsignaturamalla:
        return {'resp': 'error', 'msg': 'No existe configurado los requisitos en las asignaturas de la malla, por favor los requisitos en las asignaturas'}
    if len(eRequisitosAsignaturamalla) > len(eRequisitosTitulacionMalla):
        return {'resp': 'error', 'msg': 'Existe más requisitos configurados que el total de requisitos en la malla, por favor virifique el total de requisitos en las asignaturas' }

    for rasgmalla in eRequisitosAsignaturamalla:
        requisitomateri = RequisitoMateriaUnidadIntegracionCurricular.objects.filter(materia=materia, requisito=rasgmalla.requisito).first()
        if requisitomateri:
            requisitomateri.orden = rasgmalla.orden
            requisitomateri.activo = rasgmalla.activo
            requisitomateri.inscripcion = rasgmalla.obligatorio
            requisitomateri.titulacion = True
            requisitomateri.enlineamatriculacion = rasgmalla.enlineamatriculacion
            requisitomateri.save(request)
    materia.crear_actualizar_requisitos_uic()
    return {'resp': 'ok'}

def actualiza_usuario_revisa_actividad(request, profesor, criterio, distributivo, accion):
    try:
        from inno.models import UserCriterioRevisorIntegrantes
        if criterio.criterio.id.__str__() in variable_valor('USER_CRITERIOS_IDS'):
            if ('servidor' in request.POST and int(request.POST['servidor']) == 1) or int(criterio.criterio.id) == 186: #DIRECTOR DE CARRERA DE GRADO
                eServidor = distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=distributivo.periodo, tipo=1, status=True).first() #Decano
            else:
                eServidor = distributivo.carrera.coordinadorcarrera_set.filter(sede=distributivo.coordinacion.sede, tipo=3, periodo=distributivo.periodo, status=True).first() #Director(a) de carrera
            listadopersonas = criterio.usercriteriorevisor_set.filter(status=True)
            if eServidor and accion == 'add':
                if revisor := listadopersonas.filter(tiporevisor=1, rol=1, persona=eServidor.persona).first(): #1 'EVIDENCIA')
                    if not UserCriterioRevisorIntegrantes.objects.values('id').filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).exists():
                        user = UserCriterioRevisorIntegrantes(usuariorevisor=revisor, profesor_id=profesor.id, status=True)
                        user.save(request)
                if revisor := listadopersonas.filter(tiporevisor=2, rol=1, persona=eServidor.persona).first(): #2 'BITACORA'
                    if not UserCriterioRevisorIntegrantes.objects.values('id').filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).exists():
                        user = UserCriterioRevisorIntegrantes(usuariorevisor=revisor, profesor_id=profesor.id, status=True)
                        user.save(request)
            if eServidor and accion == 'del':
                if revisor := listadopersonas.filter(tiporevisor=1, rol=1, persona=eServidor.persona).first():  # 1 'EVIDENCIA')
                    if UserCriterioRevisorIntegrantes.objects.values('id').filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).exists():
                        user = UserCriterioRevisorIntegrantes.objects.filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).first()
                        user.usuario_modificacion_id = 1
                        user.fecha_modificacion = datetime.now()
                        user.status = False
                        user.save(request)
                if revisor := listadopersonas.filter(tiporevisor=2, rol=1, persona=eServidor.persona).first(): #2 'BITACORA'
                    if UserCriterioRevisorIntegrantes.objects.values('id').filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).exists():
                        user = UserCriterioRevisorIntegrantes.objects.filter(usuariorevisor=revisor, profesor_id=profesor.id, status=True).first()
                        user.usuario_modificacion_id = 1
                        user.fecha_modificacion = datetime.now()
                        user.status = False
                        user.save(request)
    except Exception as ex:
        pass


def actualizar_resumen(self, idm):
    from sga.models import RubricaPreguntas, Materia, RespuestaEvaluacionAcreditacion, RespuestaRubrica
    from posgrado.models import RespuestaRubricaPosgrado
    from decimal import Decimal
    try:
        estado = 'no procesado'
        eMateria = Materia.objects.get(status=True, pk=int(idm))
        tablaponderacion = self.distributivo.tablaponderacion
        if self.distributivo.periodo.periodoacademia_set.filter(status=True)[0].versioninstrumento == 2:
            if tablaponderacion:
                prom = sumhetero = resultadohetero = 0
                # Calcular los promedios de la hetero

                estado = True
                re = RespuestaEvaluacionAcreditacion.objects.values('evaluador_id').filter(
                    status=True,
                    tipoinstrumento=1,
                    proceso__periodo=self.distributivo.materia.nivel.periodo,
                    materia=self.distributivo.materia,
                    profesor=self.distributivo.profesor,
                    respuestarubrica__rubrica__para_hetero=True).exclude(respuestarubrica__rubrica__rvigente=True)

                if re.exists():
                    estado = False
                    rubricas_hetero = RespuestaRubrica.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=eMateria, respuestaevaluacion__profesor=self.distributivo.profesor, respuestaevaluacion__tipoinstrumento=1, status=True, rubrica__para_hetero=True, rubrica__rvigente=estado).distinct()
                else:
                    rubricas_hetero = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=eMateria, respuestaevaluacion__profesor=self.distributivo.profesor, respuestaevaluacion__tipoinstrumento=1, status=True, rubrica__para_hetero=True, rubrica__rvigente=estado).distinct()

                rubricapreguntas_hetero = RubricaPreguntas.objects.filter(rubrica__id__in=rubricas_hetero)

                if rubricapreguntas_hetero:
                    for rubri in rubricapreguntas_hetero:
                        sumhetero += rubri.promedio

                    prom = round(sumhetero/rubricapreguntas_hetero.count(), 2)
                    resultadohetero = (prom * Decimal(tablaponderacion.docencia_instrumentohetero))/100

                promauto = sumauto = resultadoauto = 0
                # Calcular los promedios de la auto

                rubricas_auto = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=eMateria, respuestaevaluacion__profesor=self.distributivo.profesor, respuestaevaluacion__tipoinstrumento=2, status=True, rubrica__para_auto=True).distinct()
                rubricapreguntas_auto = RubricaPreguntas.objects.filter(rubrica__in=rubricas_auto)

                if rubricapreguntas_auto:
                    for rubri in rubricapreguntas_auto:
                        sumauto += rubri.promedio

                    promauto = round(sumauto/rubricapreguntas_auto.count(), 2)
                    resultadoauto = (promauto * Decimal(tablaponderacion.docencia_instrumentoauto))/100

                promdir = sumdir = resultadodir = 0
                # Calcular los promedios de la directivos

                rubricas_dir = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=eMateria, respuestaevaluacion__profesor=self.distributivo.profesor, respuestaevaluacion__tipoinstrumento=4, status=True, rubrica__para_directivo=True).distinct()
                rubricapreguntas_dir = RubricaPreguntas.objects.filter(rubrica__in=rubricas_dir)
                if rubricapreguntas_dir:
                    for rubri in rubricapreguntas_dir:
                        sumdir += rubri.promedio

                    promdir = round(sumdir/rubricapreguntas_dir.count(), 2)
                    resultadodir = (promdir * Decimal(tablaponderacion.docencia_instrumentodirectivo))/100

                self.promedio_docencia_hetero = prom
                self.promedio_docencia_auto = promauto
                self.promedio_docencia_directivo = promdir

                self.valor_tabla_docencia_hetero = round(resultadohetero, 2)
                self.valor_tabla_docencia_auto = round(resultadoauto, 2)
                self.valor_tabla_docencia_directivo = round(resultadodir, 2)

                self.resultado_docencia = round(resultadohetero, 2) + round(resultadoauto, 2) + round(resultadodir, 2)
                self.resultado_total = self.resultado_docencia
                self.save()

                estado = 'procesado'
        return estado
    except Exception as ex:
        pass

def cantidad_evaluacion_docente(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    try:
        estado = True
        re = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
            status=True,
            tipoinstrumento=1,
            proceso__periodo=self.materia.nivel.periodo,
            materia=self.materia,
            profesor=self.profesor,
            respuestarubricaposgrado__rubrica__para_hetero=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)
        if re.exists():
            estado = False

        resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(status=True,tipoinstrumento=1,profesor=self.profesor,materia=self.materia, respuestarubricaposgrado__rubrica__para_hetero=True, respuestarubricaposgrado__rubrica__rvigente=estado)
        if resultados.exists():
            return resultados.distinct().count()
        return 0
    except Exception as ex:
        pass

def ids_eval_zero(ids):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sga.models import ProfesorMateria
    try:
        lista = []
        eProfesorMaterias = ProfesorMateria.objects.filter(status=True, id__in=ids)
        for eProfesorMateria in eProfesorMaterias:
            if cantidad_evaluacion_docente(eProfesorMateria) == 0:
                lista.append(eProfesorMateria.materia.id)
        return lista
    except Exception as ex:
        pass

def ids_eval_auto(ids):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sga.models import ProfesorMateria
    try:
        lista = []
        eProfesorMaterias = ProfesorMateria.objects.filter(status=True, id__in=ids)
        for eProfesorMateria in eProfesorMaterias:
            if cantidad_evaluacion_directivos(eProfesorMateria) == 0:
                lista.append(eProfesorMateria.materia.id)
        return lista
    except Exception as ex:
        pass

def ids_eval_director(ids):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sga.models import ProfesorMateria
    try:
        lista = []
        eProfesorMaterias = ProfesorMateria.objects.filter(status=True, id__in=ids)
        for eProfesorMateria in eProfesorMaterias:
            if not evaluo_director(eProfesorMateria):
                lista.append(eProfesorMateria.materia.id)
        return lista
    except Exception as ex:
        pass

def ids_eval_coordinador(ids):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sga.models import ProfesorMateria
    try:
        lista = []
        eProfesorMaterias = ProfesorMateria.objects.filter(status=True, id__in=ids)
        for eProfesorMateria in eProfesorMaterias:
            if not evaluo_coordinador(eProfesorMateria):
                lista.append(eProfesorMateria.materia.id)
        return lista
    except Exception as ex:
        pass

def cantidad_evaluacion_directivos(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    try:
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(status=True,tipoinstrumento=4,profesor=self.profesor,materia=self.materia, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            return resultados.distinct().count()
        return 0
    except Exception as ex:
        pass

def evaluo_coordinador(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from posgrado.models import CohorteMaestria
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=self.profesor,materia=self.materia, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            for resultado in resultados:
                if CohorteMaestria.objects.filter(status=True, coordinador=resultado.evaluador,
                                                  maestriaadmision__carrera=resultado.materia.asignaturamalla.malla.carrera).exists():
                    estado = True
        return estado
    except Exception as ex:
        pass

def evaluo_director(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sagest.models import Departamento
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=self.profesor,materia=self.materia, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            for resultado in resultados:
                if Departamento.objects.filter(pk=216, responsable=resultado.evaluador).exists():
                    estado = True
                elif Departamento.objects.filter(pk=215, responsable=resultado.evaluador).exists():
                    estado = True
                elif Departamento.objects.filter(pk=163, responsable=resultado.evaluador).exists():
                    estado = True
        return estado
    except Exception as ex:
        pass

def evaluo_coordinador_2(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from posgrado.models import CohorteMaestria
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=self.evaluado,materia=self.materia, evaluador=self.evaluador, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            estado = True
            self.evalua = True
            self.save()
        return estado
    except Exception as ex:
        pass

def evaluo_director_2(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    from sagest.models import Departamento
    try:
        estado = False
        resultados=RespuestaEvaluacionAcreditacionPosgrado.objects.filter(status=True,tipoinstrumento=4,profesor=self.evaluado, materia=self.materia, evaluador=self.evaluador, respuestarubricaposgrado__rubrica__para_directivo=True)
        if resultados.exists():
            estado = True
            self.evalua = True
            self.save()
        return estado
    except Exception as ex:
        pass

def cantidad_evaluacion_auto(self):
    from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado
    try:
        resultados = RespuestaEvaluacionAcreditacionPosgrado.objects.values('profesor_id').filter(status=True,tipoinstrumento=2,profesor=self.profesor,materia=self.materia, respuestarubricaposgrado__rubrica__para_auto=True)
        if resultados.exists():
            return resultados.distinct().count()
        return 0
    except Exception as ex:
        pass

def frecuencia_preguntas_hetero(self):
    from sga.models import RubricaPreguntas
    from posgrado.models import RespuestaRubricaPosgrado, RespuestaEvaluacionAcreditacionPosgrado
    try:
        totalencuestado = cantidad_evaluacion_docente(self)

        estado = True
        re = RespuestaEvaluacionAcreditacionPosgrado.objects.values('evaluador_id').filter(
            status=True,
            tipoinstrumento=1,
            proceso__periodo=self.materia.nivel.periodo,
            materia=self.materia,
            profesor=self.profesor,
            respuestarubricaposgrado__rubrica__para_hetero=True).exclude(respuestarubricaposgrado__rubrica__rvigente=True)
        if re.exists():
            estado = False

        rubricas = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=self.materia, status=True, rubrica__para_hetero=True, rubrica__rvigente=estado).distinct()
        preguntasrubricas = RubricaPreguntas.objects.filter(rubrica__in=rubricas)

        cursor = connections['sga_select'].cursor()
        sql = f"""
            SELECT 
                R0.texto_nosatisfactorio, 
                R0.texto_basico, 
                R0.texto_competente, 
                R0.texto_muycompetente, 
                R0.texto_destacado,  
                DRR0.valor,
                RP0.id,
                COUNT(DRR0.valor) AS "VALOR"
            FROM posgrado_detallerespuestarubricapos DRR0
                INNER JOIN sga_rubricapreguntas RP0 ON RP0.id = DRR0.rubricapregunta_id
                INNER JOIN sga_rubrica R0 ON R0.id = RP0.rubrica_id
                INNER JOIN posgrado_respuestarubricaposgrado RR0 ON RR0.id = DRR0.respuestarubrica_id
                INNER JOIN posgrado_respuestaevaluacionacreditacionposgrado REA ON REA.id = RR0.respuestaevaluacion_id
            WHERE 
                DRR0.rubricapregunta_id IN {tuple(preguntasrubricas.values_list('id', flat=True))} AND 
                REA.materia_id = {self.materia.pk} AND REA.profesor_id = {self.profesor.pk} AND
                DRR0."status" AND RP0."status" AND R0."status" AND RR0."status" AND REA."status"
            GROUP BY R0.texto_nosatisfactorio, R0.texto_basico, R0.texto_competente, R0.texto_muycompetente, R0.texto_destacado, DRR0.valor, RP0.id
            ORDER BY DRR0.valor
        """
        cursor.execute(sql)
        listadetalle = cursor.fetchall()
        newList = []
        for rubrica in preguntasrubricas:
            lista, listavalida =  [], []
            cuenta1, cuenta2, cuenta3, cuenta4, cuenta5, valida = 0, 0, 0, 0, 0, 0
            sumporcentajefi = 0
            newDetailList = filter(lambda x: x[6] == rubrica.pk, listadetalle)
            for lis in newDetailList:
                porcentajefi = 0
                if rubrica.pk == lis[6]:
                    if valida == 0:
                        listavalida, valida = [lis[0], lis[1], lis[2], lis[3], lis[4]], 1

                    porcentaje = round(null_to_decimal((lis[7] * 100) / totalencuestado), 2)
                    if lis[5] == 1:
                        cuenta1 = 1
                        lista.append([lis[0], lis[5], lis[7], porcentaje])
                        porcentajefi = round(1 * porcentaje, 2)
                    if lis[5] == 2:
                        cuenta2 = 1
                        lista.append([lis[1], lis[5], lis[7], porcentaje])
                        porcentajefi = round(2 * porcentaje, 2)
                    if lis[5] == 3:
                        cuenta3 = 1
                        lista.append([lis[2], lis[5], lis[7], porcentaje])
                        porcentajefi = round(3 * porcentaje, 2)
                    if lis[5] == 4:
                        cuenta4 = 1
                        lista.append([lis[3], lis[5], lis[7], porcentaje])
                        porcentajefi = round(4 * porcentaje, 2)
                    if lis[5] == 5:
                        cuenta5 = 1
                        lista.append([lis[4], lis[5], lis[7], porcentaje])
                        porcentajefi = round(5 * porcentaje, 2)

                sumporcentajefi += porcentajefi

            rubrica.promedio = round(sumporcentajefi/100, 2)
            rubrica.save()

            if len(listavalida) > 0:
                if cuenta1 == 0: lista.append([listavalida[0], 1, 0, 0])
                if cuenta2 == 0: lista.append([listavalida[1], 2, 0, 0])
                if cuenta3 == 0: lista.append([listavalida[2], 3, 0, 0])
                if cuenta4 == 0: lista.append([listavalida[3], 4, 0, 0])
                if cuenta5 == 0: lista.append([listavalida[4], 5, 0, 0])

            lista = sorted(lista, key=lambda x: x[1])
            newList.append({'rubrica':rubrica, 'data':lista})

        return newList
    except Exception as ex:
        pass

def frecuencia_preguntas_auto(self):
    from sga.models import RubricaPreguntas
    from posgrado.models import RespuestaRubricaPosgrado
    try:
        totalencuestado = cantidad_evaluacion_auto(self)
        rubricas = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=self.materia, status=True, rubrica__para_auto=True).distinct()
        preguntasrubricas = RubricaPreguntas.objects.filter(rubrica__in=rubricas)

        cursor = connections['sga_select'].cursor()
        sql = f"""
            SELECT 
                R0.texto_nosatisfactorio, 
                R0.texto_basico, 
                R0.texto_competente, 
                R0.texto_muycompetente, 
                R0.texto_destacado,  
                DRR0.valor,
                RP0.id,
                COUNT(DRR0.valor) AS "VALOR"
            FROM posgrado_detallerespuestarubricapos DRR0
                INNER JOIN sga_rubricapreguntas RP0 ON RP0.id = DRR0.rubricapregunta_id
                INNER JOIN sga_rubrica R0 ON R0.id = RP0.rubrica_id
                INNER JOIN posgrado_respuestarubricaposgrado RR0 ON RR0.id = DRR0.respuestarubrica_id
                INNER JOIN posgrado_respuestaevaluacionacreditacionposgrado REA ON REA.id = RR0.respuestaevaluacion_id
            WHERE 
                DRR0.rubricapregunta_id IN {tuple(preguntasrubricas.values_list('id', flat=True))} AND 
                REA.materia_id = {self.materia.pk} AND REA.profesor_id = {self.profesor.pk} AND
                DRR0."status" AND RP0."status" AND R0."status" AND RR0."status" AND REA."status"
            GROUP BY R0.texto_nosatisfactorio, R0.texto_basico, R0.texto_competente, R0.texto_muycompetente, R0.texto_destacado, DRR0.valor, RP0.id
            ORDER BY DRR0.valor
        """
        cursor.execute(sql)
        listadetalle = cursor.fetchall()
        newList = []
        for rubrica in preguntasrubricas:
            lista, listavalida =  [], []
            cuenta1, cuenta2, cuenta3, cuenta4, cuenta5, valida = 0, 0, 0, 0, 0, 0
            sumporcentajefi = 0
            newDetailList = filter(lambda x: x[6] == rubrica.pk, listadetalle)
            for lis in newDetailList:
                porcentajefi = 0
                if rubrica.pk == lis[6]:
                    if valida == 0:
                        listavalida, valida = [lis[0], lis[1], lis[2], lis[3], lis[4]], 1

                    porcentaje = round(null_to_decimal((lis[7] * 100) / totalencuestado), 2)
                    if lis[5] == 1:
                        cuenta1 = 1
                        lista.append([lis[0], lis[5], lis[7], porcentaje])
                        porcentajefi = round(1 * porcentaje, 2)
                    if lis[5] == 2:
                        cuenta2 = 1
                        lista.append([lis[1], lis[5], lis[7], porcentaje])
                        porcentajefi = round(2 * porcentaje, 2)
                    if lis[5] == 3:
                        cuenta3 = 1
                        lista.append([lis[2], lis[5], lis[7], porcentaje])
                        porcentajefi = round(3 * porcentaje, 2)
                    if lis[5] == 4:
                        cuenta4 = 1
                        lista.append([lis[3], lis[5], lis[7], porcentaje])
                        porcentajefi = round(4 * porcentaje, 2)
                    if lis[5] == 5:
                        cuenta5 = 1
                        lista.append([lis[4], lis[5], lis[7], porcentaje])
                        porcentajefi = round(5 * porcentaje, 2)

                sumporcentajefi += porcentajefi

            rubrica.promedio = round(sumporcentajefi/100, 2)
            rubrica.save()

            if len(listavalida) > 0:
                if cuenta1 == 0: lista.append([listavalida[0], 1, 0, 0])
                if cuenta2 == 0: lista.append([listavalida[1], 2, 0, 0])
                if cuenta3 == 0: lista.append([listavalida[2], 3, 0, 0])
                if cuenta4 == 0: lista.append([listavalida[3], 4, 0, 0])
                if cuenta5 == 0: lista.append([listavalida[4], 5, 0, 0])

            lista = sorted(lista, key=lambda x: x[1])
            newList.append({'rubrica':rubrica, 'data':lista})

        return newList
    except Exception as ex:
        pass

def frecuencia_preguntas_dir(self):
    from sga.models import RubricaPreguntas
    from posgrado.models import RespuestaRubricaPosgrado
    try:
        totalencuestado = cantidad_evaluacion_directivos(self)
        rubricas = RespuestaRubricaPosgrado.objects.values_list('rubrica_id').filter(respuestaevaluacion__materia=self.materia, status=True, rubrica__para_directivo=True).distinct()
        preguntasrubricas = RubricaPreguntas.objects.filter(rubrica__in=rubricas)

        cursor = connections['sga_select'].cursor()
        sql = f"""
            SELECT 
                R0.texto_nosatisfactorio, 
                R0.texto_basico, 
                R0.texto_competente, 
                R0.texto_muycompetente, 
                R0.texto_destacado,  
                DRR0.valor,
                RP0.id,
                COUNT(DRR0.valor) AS "VALOR"
            FROM posgrado_detallerespuestarubricapos DRR0
                INNER JOIN sga_rubricapreguntas RP0 ON RP0.id = DRR0.rubricapregunta_id
                INNER JOIN sga_rubrica R0 ON R0.id = RP0.rubrica_id
                INNER JOIN posgrado_respuestarubricaposgrado RR0 ON RR0.id = DRR0.respuestarubrica_id
                INNER JOIN posgrado_respuestaevaluacionacreditacionposgrado REA ON REA.id = RR0.respuestaevaluacion_id
            WHERE 
                DRR0.rubricapregunta_id IN {tuple(preguntasrubricas.values_list('id', flat=True))} AND 
                REA.materia_id = {self.materia.pk} AND REA.profesor_id = {self.profesor.pk} AND
                DRR0."status" AND RP0."status" AND R0."status" AND RR0."status" AND REA."status"
            GROUP BY R0.texto_nosatisfactorio, R0.texto_basico, R0.texto_competente, R0.texto_muycompetente, R0.texto_destacado, DRR0.valor, RP0.id
            ORDER BY DRR0.valor
        """
        cursor.execute(sql)
        listadetalle = cursor.fetchall()
        newList = []
        for rubrica in preguntasrubricas:
            lista, listavalida =  [], []
            cuenta1, cuenta2, cuenta3, cuenta4, cuenta5, valida = 0, 0, 0, 0, 0, 0
            sumporcentajefi = 0
            newDetailList = filter(lambda x: x[6] == rubrica.pk, listadetalle)
            for lis in newDetailList:
                porcentajefi = 0
                if rubrica.pk == lis[6]:
                    if valida == 0:
                        listavalida, valida = [lis[0], lis[1], lis[2], lis[3], lis[4]], 1

                    porcentaje = round(null_to_decimal((lis[7] * 100) / totalencuestado), 2)
                    if lis[5] == 1:
                        cuenta1 = 1
                        lista.append([lis[0], lis[5], lis[7], porcentaje])
                        porcentajefi = round(1 * porcentaje, 2)
                    if lis[5] == 2:
                        cuenta2 = 1
                        lista.append([lis[1], lis[5], lis[7], porcentaje])
                        porcentajefi = round(2 * porcentaje, 2)
                    if lis[5] == 3:
                        cuenta3 = 1
                        lista.append([lis[2], lis[5], lis[7], porcentaje])
                        porcentajefi = round(3 * porcentaje, 2)
                    if lis[5] == 4:
                        cuenta4 = 1
                        lista.append([lis[3], lis[5], lis[7], porcentaje])
                        porcentajefi = round(4 * porcentaje, 2)
                    if lis[5] == 5:
                        cuenta5 = 1
                        lista.append([lis[4], lis[5], lis[7], porcentaje])
                        porcentajefi = round(5 * porcentaje, 2)

                sumporcentajefi += porcentajefi

            rubrica.promedio = round(sumporcentajefi/100, 2)
            rubrica.save()

            if len(listavalida) > 0:
                if cuenta1 == 0: lista.append([listavalida[0], 1, 0, 0])
                if cuenta2 == 0: lista.append([listavalida[1], 2, 0, 0])
                if cuenta3 == 0: lista.append([listavalida[2], 3, 0, 0])
                if cuenta4 == 0: lista.append([listavalida[3], 4, 0, 0])
                if cuenta5 == 0: lista.append([listavalida[4], 5, 0, 0])

            lista = sorted(lista, key=lambda x: x[1])
            newList.append({'rubrica':rubrica, 'data':lista})

        return newList
    except Exception as ex:
        pass


def respuestasevaluacionaccionmejoras(self, periodo, profesor, tipo):
    if tipo == 1:
        return self.respuestaevaluacionacreditacion_set.filter(status=True, accionmejoras__isnull=False,
                                                               tipoinstrumento=tipo,
                                                               proceso__periodo=periodo, profesor=profesor,
                                                               materiaasignada__isnull=False)
    else:
        return self.respuestaevaluacionacreditacion_set.filter(status=True, accionmejoras__isnull=False,
                                                               tipoinstrumento=tipo,
                                                               proceso__periodo=periodo, profesor=profesor)

def respuestasevaluacionformacioncontinua(self, periodo, profesor, tipo):
    if tipo == 1:
        return self.respuestaevaluacionacreditacion_set.filter(status=True, formacioncontinua__isnull=False,
                                                               tipoinstrumento=tipo,
                                                               proceso__periodo=periodo, profesor=profesor,
                                                               materiaasignada__isnull=False)
    else:
        return self.respuestaevaluacionacreditacion_set.filter(status=True, formacioncontinua__isnull=False,
                                                               tipoinstrumento=tipo,
                                                               proceso__periodo=periodo, profesor=profesor)

def entero_a_romano(num):
    try:
        if not isinstance(num, int) or num <= 0:
            return "novalido"

        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num
    except Exception as ex:
        pass

def calcular_hash(archivo):
    import hashlib
    hasher = hashlib.sha256()
    for chunk in archivo.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()

def verifica_docs_duplicados(list_archivos):
    archivos_hashes = {}
    duplicados = []
    for archivo in list_archivos:
        archivo_hash = calcular_hash(archivo)
        if archivo_hash in archivos_hashes:
            duplicados.append(archivo.name)
        else:
            archivos_hashes[archivo_hash] = archivo
    if duplicados:
        return {'e_duplicado': True, 'n_duplicados': duplicados}
    return {'e_duplicado': False}
