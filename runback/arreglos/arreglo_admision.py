#!/usr/bin/env python
import os
import sys
import openpyxl
# import urllib2

# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sagest.models import *
from sga.funciones import cuenta_email_disponible
from clrncelery.models import BatchTasks
from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO
from sga.My_Model.SubirMatrizSENESCYT import My_SubirMatrizInscripcion, My_RegistroTareaSubirMatrizInscripcion, \
    My_HistorialProcesoSubirMatrizInscripcion, My_HistorialSubirMatrizInscripcion


def processMatrizSENESCYT(persona_id, matriz_id, periodo_id):
    persona = Persona.objects.get(pk=persona_id)
    matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
    periodo = Periodo.objects.get(pk=periodo_id)
    matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=4).update(estado=1)
    procesos = matriz.procesos()
    for proceso in procesos:
        print(proceso)
        siguiente_proceso = matriz.siguiente_proceso()
        if not siguiente_proceso:
            print("break")
            break
        if proceso.id == siguiente_proceso.id:
            if proceso.estado == 1 or proceso.estado == 3:
                veProcess = False
                vrProcess = False
                if 'VALIDA_MATRIZ' == proceso.proceso.accion:
                    vrProcess = matriz.validar_matriz_senescyt(proceso, persona)
                    print("Validar matrizas")
                    print(vrProcess)
                    veProcess = True
                elif 'CREA_PERSONA' == proceso.proceso.accion:
                    vrProcess = matriz.crear_persona_senescyt(proceso, persona)
                    print("crear personas")
                    print(vrProcess)
                    veProcess = True
                elif 'CREA_INSCRIPCION' == proceso.proceso.accion:
                    vrProcess = matriz.crear_inscripcion_senescyt(proceso, persona)
                    veProcess = True
                elif 'CREA_PERFIL' == proceso.proceso.accion:
                    vrProcess = matriz.crear_inscripcion_perfil_senescyt(proceso, persona)
                    veProcess = True
                if veProcess:
                    proceso.estado = 3 if not vrProcess else 2
                    proceso.save(usuario_id=persona.usuario.id)
                    if not vrProcess:
                        break
    total = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True).count()
    total_success = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=2).count()
    if total == total_success:
        matriz.estado = 2
        matriz.save(usuario_id=persona.usuario.id)

def processMatriculaMatrizSENESCYT(persona_id, matriz_id, periodo_id, carrera_id):
    print("entra al proceso")
    persona = Persona.objects.get(pk=persona_id)
    matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
    periodo = Periodo.objects.get(pk=periodo_id)
    title = body = ''
    carrera = None
    content_type = None
    object_id = None
    proceso = 0
    if carrera_id:
        carrera = Carrera.objects.get(pk=carrera_id)
        vrProcess = matriz.matriculacion_senescyt(periodo, persona, carrera)
    else:
        vrProcess = matriz.matriculacion_senescyt(periodo, persona)

##primero procesar la matriz subida al sistema
#processMatrizSENESCYT(1, 1, 123)
## luego matricular de acuerdo al distributido puede ser por carrera o general; si es general carrera_id=None
#processMatriculaMatrizSENESCYT(1, 1, 123, 83)
matriz = My_SubirMatrizInscripcion.objects.filter(pk=1)
historial_proceso_perfil = My_HistorialProcesoSubirMatrizInscripcion.objects.filter(status=True, proceso__accion='CREA_PERFIL', matriz=matriz)
historial_proceso_perfil_observaciones_success = My_HistorialSubirMatrizInscripcion.objects.filter(status=True, estado=1, historial=historial_proceso_perfil[0])
observaciones_success = historial_proceso_perfil_observaciones_success[0].observaciones()
sede = Sede.objects.get(pk=1)
periodo = Periodo.objects.get(pk=123)
oCarrera = Carrera.objects.get(pk=99)
niveles = Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID)
sesiones = Sesion.objects.filter(pk__in=Nivel.objects.filter(periodo=periodo, nivellibrecoordinacion__coordinacion=ADMISION_ID).distinct().values_list('sesion_id'))
linea = 1
for arrDataSuccess in observaciones_success[0].observacion:
    inscripcion_id = arrDataSuccess['INSCRIPCION_ID']
    modalidad_id = arrDataSuccess['MODALIDAD_ID']
    carrera_id = arrDataSuccess['CARRERA_ID']
    gratuidad = arrDataSuccess['GRATUIDAD']
    inscripcion = None
    carrera = None

    if Inscripcion.objects.filter(pk=inscripcion_id).exists():
        inscripcion = Inscripcion.objects.get(pk=inscripcion_id)
    if Carrera.objects.filter(pk=carrera_id).exists():
        carrera = Carrera.objects.get(pk=carrera_id)

    if oCarrera.id == carrera.id:
        print("****************************************************************")
        print("** %s - %s - %s" % (linea, carrera, inscripcion))
        inscripcion = Inscripcion.objects.get(pk=inscripcion_id, carrera=carrera)
        mimalla = inscripcion.malla_inscripcion()
        nivel = Nivel.objects.get(periodo=periodo, sesion=inscripcion.sesion, sede=sede)

        matricula = Matricula.objects.filter(inscripcion=inscripcion, nivel=nivel)
        if matricula.exists():
            matricula = matricula.first()
            if MateriaAsignada.objects.filter(matricula=matricula).count() > 3:
                materiasignada = MateriaAsignada.objects.filter(matricula=matricula, materia_id=44242)
                if materiasignada.exists():
                    materiasignada = materiasignada.first()
                    materiasignada.delete()
                    print("elimina asignatura %s" % materiasignada.materia.asignatura)

            asignaturas = Asignatura.objects.filter(pk__in=Materia.objects.values_list('asignatura_id').filter(nivel__periodo_id=123, asignaturamalla__malla__carrera=carrera).distinct())
            for asignatura in asignaturas:
                materiaparalelo = None
                for materia in Materia.objects.filter(nivel__periodo_id=123, asignaturamalla__malla__carrera=carrera, asignatura=asignatura):
                    matriculados = MateriaAsignada.objects.filter(materia=materia).count()
                    if matriculados < materia.cupo:
                        materiaparalelo = materia
                        break
                if materiaparalelo:
                    if not MateriaAsignada.objects.values('id').filter(matricula=matricula, materia__asignatura=asignatura).exists():
                        matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materiaparalelo.asignatura, fecha__lt=materiaparalelo.nivel.fin).count() + 1
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=0,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO,
                                                          cobroperdidagratuidad=not gratuidad)
                        materiaasignada.save()
                        materiaasignada.asistencias()
                        materiaasignada.evaluacion()
                        materiaasignada.mis_planificaciones()
                        materiaasignada.save()
                        print(materiaasignada)
            matricula.actualizar_horas_creditos()
            matricula.estado_matricula = 2
            matricula.save()
            matricula.calcula_nivel()
            inscripcion.actualizar_nivel()
            if Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula).exists():
                num_materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True).exclude(materia__asignatura_id=4837).count()
                if num_materias > 0:
                    valor_x_materia = 15
                    valor_total = num_materias * valor_x_materia
                    matricula.estado_matricula = 1
                    matricula.save()
                    rubro = Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula).first()
                    rubro.valortotal = valor_total
                    rubro.valor = valor_total
                    rubro.saldo = valor_total
                    print(rubro)
        linea += 1







"""REPETIDORES"""
oCarreraIdiomasENLINEA = Carrera.objects.get(pk=101)
repetidores = Matricula.objects.filter(status=True, inscripcion__carrera=oCarreraIdiomasENLINEA, aprobado=False, nivel__periodo_id=99, inscripcion__fecha__gte=datetime(2020, 12, 11)).values_list('id')
matriculas = Matricula.objects.filter(inscripcion__carrera=oCarreraIdiomasENLINEA, nivel__periodo_id=123)
for matricula_actual in matriculas:
    inscripcion = matricula_actual.inscripcion
    if Matricula.objects.filter(status=True, inscripcion=inscripcion, aprobado=False, nivel__periodo_id=99).exists():
        matricula_anterior = Matricula.objects.filter(status=True, inscripcion=inscripcion, aprobado=False, nivel__periodo_id=99).first()
        for asignatura in MateriaAsignada.objects.filter(matricula=matricula_anterior, estado_id=2):
            if not MateriaAsignada.objects.filter(matricula=matricula_actual, materia__asignatura=asignatura.materia.asignatura).exists():
                paralelo = None
                for materia_actual in Materia.objects.filter(nivel__periodo_id=123, asignatura_id=asignatura.materia.asignatura.id, asignaturamalla__malla__carrera=inscripcion.carrera):
                    matriculados = MateriaAsignada.objects.filter(materia=materia_actual).count()
                    cupo = materia_actual.cupo
                    if matriculados < cupo:
                        paralelo = materia_actual.paralelomateria
                        break
                if paralelo:
                    materia = Materia.objects.filter(nivel__periodo_id=123, asignatura_id=asignatura.materia.asignatura.id, paralelomateria=paralelo, asignaturamalla__malla__carrera=inscripcion.carrera).first()
                    num_matriculas = matricula_actual.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=asignatura.materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                    materiaasignada = MateriaAsignada(matricula=matricula_actual,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      matriculas=num_matriculas,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO,
                                                      cobroperdidagratuidad=True)
                    materiaasignada.save()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save()
                    print(materiaasignada)
        if Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula_actual).exists():
            num_materias = MateriaAsignada.objects.filter(matricula=matricula_actual, cobroperdidagratuidad=True).exclude(materia__asignatura_id=4837).count()
            if num_materias > 0:
                valor_x_materia = 15
                valor_total = num_materias * valor_x_materia
                matricula_actual.estado_matricula = 1
                matricula_actual.save()
                rubro = Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula_actual).first()
                rubro.valortotal = valor_total
                rubro.valor = valor_total
                rubro.saldo = valor_total
                print(rubro)






"""
def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

def calculate_username(persona, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = persona.nombres.lower().split(' ')
    while '' in s:
        s.remove('')
    if persona.apellido2:
        usernamevariant = s[0][0] + persona.apellido1.lower() + persona.apellido2.lower()[0]
    else:
        usernamevariant = s[0][0] + persona.apellido1.lower()
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)
    if not User.objects.values('id').filter(username=usernamevariantfinal).exclude(persona=persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username(persona, variant + 1)

def generar_usuario(persona, usuario, group_id):
    password = DEFAULT_PASSWORD
    if CLAVE_USUARIO_CEDULA:
        password = persona.cedula
    user = User.objects.create_user(usuario, '', password)
    user.save()
    persona.usuario = user
    persona.save()
    persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()

def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

# alumnos del PRE nuevos ddd
workbook = xlrd.open_workbook("admitidosadm2020_2s_septimo.xlsx")
sheet = workbook.sheet_by_index(0)
linea = 1
cedula = 0
carrera = 0
# periodo = Periodo.objects.get(pk=95)
periodo = Periodo.objects.get(pk=99)
sede = Sede.objects.get(pk=1)
import time
try:
    for rowx in range(sheet.nrows):
        if linea>1:
            cols = sheet.row_values(rowx)
            #virtual
            #session_id = 13
            #presencial
            session_id = int(cols[13])
            cedula = cols[0].strip().upper()
            # pais=None
            # paisnac=None
            # provincia=None
            # canton=None
            persona=None
            # email=None
            mimalla=None
            if Persona.objects.filter(cedula=cedula, status=True).exists():
                persona = Persona.objects.get(cedula=cedula, status=True)
            if Persona.objects.filter(pasaporte=cedula, status=True).exists():
                persona = Persona.objects.get(pasaporte=cedula, status=True)
            if not persona:
                apellido1=str(cols[1].strip())
                apellido2=str(cols[2].strip())
                nombres=str(cols[3].strip())
                if not type(cols[4]) is str:
                    nacimiento = datetime(*xlrd.xldate_as_tuple(cols[4], workbook.datemode)) if cols[4] else datetime.now().date()
                else:
                    nacimiento = convertirfecha2(cols[4])
                paisnac = Pais.objects.get(id=int(cols[10]))
                sexo=int(cols[5])
                email = str(cols[16].strip())
                convencional = str(cols[19].strip())
                telefono = str(cols[18].strip())
                provincia=str(cols[24].strip())
                canton=str(cols[25].strip())
                if Provincia.objects.filter(status=True,nombre=provincia).exists():
                    provincia = Provincia.objects.filter(status=True, nombre=provincia)[0]
                    pais = provincia.pais_id
                    if Canton.objects.filter(status=True, nombre=canton, provincia=provincia).exists():
                        canton = Canton.objects.filter(status=True, nombre=canton, provincia=provincia)[0]
                    else:
                        canton = Canton.objects.get(id=2)
                else:
                    canton=Canton.objects.get(id=2)
                    provincia = canton.provincia
                    pais = provincia.pais_id
                persona = Persona(cedula=cedula,
                                  apellido1=apellido1,
                                  apellido2=apellido2,
                                  nombres=nombres,
                                  sexo_id=sexo,
                                  nacimiento=nacimiento,
                                  paisnacimiento =paisnac,
                                  provincianacimiento =None,
                                  cantonnacimiento=None,
                                  pais_id=pais,
                                  provincia=provincia,
                                  canton=canton,
                                  email=email,
                                  telefono=telefono,
                                  telefono_conv =convencional)
                persona.save()
                username = calculate_username(persona)
                usuario = generar_usuario(persona, username, ALUMNOS_GROUP_ID)
                if EMAIL_INSTITUCIONAL_AUTOMATICO:
                    persona.emailinst = username + '@' + EMAIL_DOMAIN
                    persona.save()
                grupo = None
            else:
                if not persona.usuario:
                    username = calculate_username(persona)
                    usuario = generar_usuario(persona, username, ALUMNOS_GROUP_ID)
                    if EMAIL_INSTITUCIONAL_AUTOMATICO:
                        persona.emailinst = username + '@' + EMAIL_DOMAIN
                        persona.save()
                else:
                    if persona.usuario:
                        user = persona.usuario
                        user.set_password(persona.cedula)
                        user.save()
                        persona.cambiar_clave()
            sesion = Sesion.objects.get(id=session_id)
            idcarrera=int(cols[6])
            carrera = Carrera.objects.get(pk=idcarrera)
            modalidad = Modalidad.objects.get(pk=int(cols[8]))
            if not Inscripcion.objects.values('id').filter(status=True,persona=persona,carrera=carrera).exists():
                #inscripcion = Inscripcion.objects.filter(persona=persona, carrera=carrera)[0]
                #inscripcion.actualizar_nivel()
                #inscripcion.save()
                inscripcion = Inscripcion(persona=persona,
                                          fecha=datetime.now().date(),
                                          carrera=carrera,
                                          modalidad=modalidad,
                                          sede=sede,
                                          colegio="N/S")
                inscripcion.save()
                persona.crear_perfil(inscripcion=inscripcion)
                documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                     titulo=False,
                                                     acta=False,
                                                     cedula=False,
                                                     votacion=False,
                                                     actaconv=False,
                                                     partida_nac=False,
                                                     pre=False,
                                                     observaciones_pre='',
                                                     fotos=False)
                documentos.save()
                preguntasinscripcion = inscripcion.preguntas_inscripcion()
                perfil_inscripcion = inscripcion.persona.mi_perfil()
                perfil_inscripcion.raza_id = int(cols[15])
                discapacidad=int(cols[29])
                if discapacidad == 0:
                    perfil_inscripcion.tienediscapacidad =  False
                elif discapacidad == 1:
                    perfil_inscripcion.tienediscapacidad = True
                perfil_inscripcion.save()
                inscripcion.malla_inscripcion()
                inscripcion.actualizar_nivel()
                # if USA_TIPOS_INSCRIPCIONES:
                #     inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                #                                                             tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                #     inscripciontipoinscripcion.save()
            else:
                inscripcion = Inscripcion.objects.filter(persona=persona,carrera=carrera)[0]
                mallaalu = inscripcion.inscripcionmalla_set.all()
                mallaalu.delete()
                inscripcion.malla_inscripcion()
                inscripcion.modalidad=modalidad
                inscripcion.sesion=sesion
                inscripcion.save()
                # perfil_inscripcion = inscripcion.persona.mi_perfil()
                # perfil_inscripcion.raza_id = int(cols[29])
                # discapacidad = int(cols[18])
                # if discapacidad == 0:
                #     perfil_inscripcion.tienediscapacidad = False
                # elif discapacidad == 1:
                #     perfil_inscripcion.tienediscapacidad = True
                # perfil_inscripcion.save()

            mimalla = inscripcion.malla_inscripcion()
            #virtual
            #nivel = Nivel.objects.get(periodo=periodo, id=477)
            #presencial
            nivel = Nivel.objects.get(periodo=periodo, id=int(cols[12]))
            if not inscripcion.matricula_periodo(periodo):
                matricula = Matricula(inscripcion=inscripcion,
                                      nivel=nivel,
                                      pago=False,
                                      iece=False,
                                      becado=False,
                                      porcientobeca=0,
                                      fecha=datetime.now().date(),
                                      hora=datetime.now().time(),
                                      fechatope=fechatope(datetime.now().date()))
                matricula.save()
            else:
                matricula = Matricula.objects.get(inscripcion=inscripcion, nivel=nivel)

            for materia in Materia.objects.filter(nivel__periodo=periodo, paralelo=cols[7].strip(), asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion):
                if not MateriaAsignada.objects.values('id').filter(matricula=matricula,materia=materia).exists():
                    matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      matriculas=matriculas,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save()
                    print(materiaasignada)
            matricula.actualizar_horas_creditos()
            matricula.estado_matricula in (2,3)
            matricula.save()
            matricula.calcula_nivel()
            inscripcion.actualizar_nivel()
            if cols[31] == 'false':
                if inscripcion.sesion_id == 13:
                    tiporubromatricula = TipoOtroRubro.objects.get(pk=3019)
                else:
                    tiporubromatricula = TipoOtroRubro.objects.get(pk=3011)

                if matricula.tipomatricula_id == 1:
                    matricula.estado_matricula = 2
                    matricula.save()

                if not Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula).exists():
                    print(cols[31])
                    rubro1 = Rubro(tipo=tiporubromatricula,
                                   persona=inscripcion.persona,
                                   matricula=matricula,
                                   nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                                   cuota=1,
                                   fecha=datetime.now().date(),
                                   fechavence=datetime.now().date() + timedelta(days=2),
                                   valor=45,
                                   iva_id=1,
                                   valoriva=0,
                                   valortotal=45,
                                   saldo=45,
                                   cancelado=False)
                    rubro1.save()
                    print(rubro1)
            if not matricula.notificadoadmision:
                mimalla = matricula.inscripcion.malla_inscripcion()
                cuenta = cuenta_email_disponible()
                titulo = "Confirmación de Matrícula Admisión 2S-2020"
                if mimalla.malla.inicio.year == 2020:
                    print("Enviando ", linea, " de ")
                    print("Procesando: ", cuenta, " - ", matricula.inscripcion.persona.identificacion(), " - ", matricula.inscripcion)
                    if matricula.inscripcion.persona.emailpersonal():
                        send_html_mail(titulo,
                                       "emails/notificacionmatricula.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'persona': matricula.inscripcion.persona,
                                        },
                                       matricula.inscripcion.persona.emailpersonal(),
                                       [],
                                       cuenta=CUENTAS_CORREOS[cuenta][1]
                                       )
                        # # Temporizador para evitar que se bloquee el servicion de gmail
                        time.sleep(3)
                        matricula.notificadoadmision = True
                        matricula.save()
        print(linea, cedula, carrera)
        linea += 1
except Exception as ex:
    print(ex)

"""
