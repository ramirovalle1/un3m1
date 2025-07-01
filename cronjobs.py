#!/usr/bin/env python

import sys
import os
import queue
import threading
import json
import time
import redis as Redis

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from datetime import datetime, timedelta
from sga.models import LeccionGrupo, Clase, Leccion, AsistenciaLeccion, TemaAsistencia, SubTemaAsistencia, Notificacion
from django.db import transaction
from sga.templatetags.sga_extras import encrypt
from settings import CLASES_CONTINUAS_AUTOMATICAS, CLASES_APERTURA_DESPUES, CLASES_HORARIO_ESTRICTO, CLASES_CIERRE_AUTOMATICA, HILOS_MAXIMOS, REDIS_HOST, REDIS_PASSWORD, REDIS_BD, REDIS_PORT
from sga.funciones import variable_valor
from sga.clases_threading import ActualizaAsistencia



def cerrar(lg):
    materiaasignadaactualiza = []
    with transaction.atomic():
        ahora = datetime.now()
        if lg.fecha < ahora.date():
            try:
                lg.abierta = False
                lg.horasalida = lg.turno.termina
                lg.save()
                lg.cerrar_lecciones(lg.turno)
                print(" CERRADA\r")
            except Exception as ex:
                transaction.set_rollback(True)
                print(f"Error al cerrar la lección grupo {lg.__str__()}")
        elif lg.turno.termina < ahora.time():
            try:
                lg.abierta = False
                lg.horasalida = lg.turno.termina
                lg.save()
                lg.cerrar_lecciones(lg.turno)
                print(" CERRADA\r")
            except Exception as ex:
                transaction.set_rollback(True)
                print(f"Error al cerrar la lección grupo {lg.__str__()}")
            if CLASES_CONTINUAS_AUTOMATICAS:
                if not LeccionGrupo.objects.values('id').filter(profesor_id=lg.profesor_id, fecha=lg.fecha, abierta=True).exists():
                    hoy = ahora.date()
                    minutos_maximos = (ahora + timedelta(minutes=CLASES_APERTURA_DESPUES)).time()
                    # materias = [x.clase.materia_id for x in lg.lecciones.all()]
                    materias = lg.lecciones.all().values_list('clase__materia_id',flat=True).order_by('clase__materia_id').distinct()
                    # claseshorario = Clase.objects.filter(activo=True, status=True, dia=lg.dia, materia__id__in=materias, profesor=lg.profesor, materia__profesormateria__principal=True, inicio__lte=hoy, fin__gte=hoy, turno__comienza__gte=lg.horasalida, turno__comienza__lte=minutos_maximos).distinct()
                    claseshorario = Clase.objects.filter(activo=True, status=True, dia=lg.dia, materia__id__in=materias, profesor_id=lg.profesor_id, inicio__lte=hoy, fin__gte=hoy, turno__comienza__gte=lg.horasalida, turno__comienza__lte=minutos_maximos).distinct()
                    if claseshorario:
                        turnoaula = claseshorario.first()
                        turno = turnoaula.turno
                        aula = turnoaula.aula
                        claseshorario = claseshorario.filter(turno_id=turno.id)
                        # SE PREGUNTA SI LA CLASE ANTERIOR ES DE TIPO PRACTICA
                        puede_continuar = True
                        for clase in claseshorario:
                            if not Leccion.objects.values('id').filter(clase_id=clase.id, fecha=datetime.now()).exists():
                                leccionanterior = lg.lecciones.filter(clase__materia_id=clase.materia_id).first()
                                if leccionanterior.clase.tipoprofesor_id == 2 and clase.tipoprofesor_id == 2:
                                    anterior_grupoprofesor_id = 0
                                    if leccionanterior.clase.grupoprofesor:
                                        if leccionanterior.clase.grupoprofesor.paralelopractica:
                                            anterior_grupoprofesor_id = leccionanterior.clase.grupoprofesor_id
                                    actual_grupoprofesor_id = 0
                                    if clase.grupoprofesor:
                                        if clase.grupoprofesor.paralelopractica:
                                            actual_grupoprofesor_id = clase.grupoprofesor_id
                                    puede_continuar = anterior_grupoprofesor_id == actual_grupoprofesor_id

                        if puede_continuar:
                            try:
                                if lecciongrupo := LeccionGrupo.objects.filter(profesor_id=lg.profesor_id, turno_id=turno.id, fecha=datetime.now()).first():
                                    lecciongrupo.status = True
                                    lecciongrupo.abierta=True
                                    lecciongrupo.automatica=True
                                    lecciongrupo.usuario_creacion_id = lg.profesor.persona.usuario_id
                                else:
                                    lecciongrupo = LeccionGrupo(profesor=lg.profesor,
                                                                turno=turno,
                                                                aula=aula,
                                                                dia=lg.dia,
                                                                fecha=datetime.now(),
                                                                horaentrada=turno.comienza,
                                                                abierta=True,
                                                                automatica=True,
                                                                contenido=lg.contenido,
                                                                estrategiasmetodologicas=lg.estrategiasmetodologicas,
                                                                observaciones=lg.observaciones,
                                                                ipingreso=lg.ipingreso,
                                                                ipexterna=lg.ipexterna)
                                lecciongrupo.save()
                                for clase in claseshorario:
                                    isRedis = False
                                    ePeriodoAcademia = clase.materia.nivel.periodo.get_periodoacademia()
                                    leccionanterior = lg.lecciones.filter(clase__materia_id=clase.materia_id).first()
                                    if eLecciones := Leccion.objects.filter(clase_id=clase.id, fecha=datetime.now()):
                                        eLecciones.update(status=True, automatica=True, usuario_creacion_id=lg.profesor.persona.usuario_id)
                                        leccion = eLecciones.first()
                                        leccion.status = True
                                        leccion.abierta = True
                                        leccion.usuario_creacion_id = lg.profesor.persona.usuario_id
                                    else:
                                        leccion = Leccion(clase=clase,
                                                          fecha=datetime.now(),
                                                          horaentrada=turno.comienza,
                                                          abierta=True,
                                                          contenido=leccionanterior.contenido,
                                                          estrategiasmetodologicas=leccionanterior.estrategiasmetodologicas,
                                                          observaciones=leccionanterior.observaciones,
                                                          ipingreso=leccionanterior.ipingreso,
                                                          ipexterna=leccionanterior.ipexterna,
                                                          automatica=True,
                                                          aperturaleccion=True)
                                    leccion.save()
                                    lecciongrupo.lecciones.add(leccion.id)
                                    for asistencias in AsistenciaLeccion.objects.filter(leccion_id=leccionanterior.id):
                                        # REGISTRO MANUAL (PRESENCIAL)
                                        if asistencias.asistio and not asistencias.virtual:
                                            vStatus = True
                                            vAsistio = True
                                            vVirtual = False
                                        # REGISTRO VIRTUAL (ESTUDIANTE)
                                        elif asistencias.asistio and asistencias.virtual:
                                            vStatus = True
                                            vAsistio = True
                                            vVirtual = True
                                        # REGISTRO MANUAL (DOCENTE)
                                        elif not asistencias.asistio and asistencias.virtual:
                                            vStatus = True
                                            vAsistio = True
                                            vVirtual = True
                                        else:
                                            vStatus = True
                                            vAsistio = False
                                            vVirtual = False
                                        if asistencialeccion := AsistenciaLeccion.objects.filter(leccion_id=leccion.id, materiaasignada_id=asistencias.materiaasignada_id):
                                            asistencialeccion.update(status=vStatus,
                                                                     asistio=vAsistio,
                                                                     virtual=vVirtual,
                                                                     usuario_creacion_id=lg.profesor.persona.usuario_id)
                                        else:
                                            asistencialeccion = AsistenciaLeccion(leccion_id=leccion.id, materiaasignada_id=asistencias.materiaasignada_id)
                                            asistencialeccion.status = vStatus
                                            asistencialeccion.asistio = vAsistio
                                            asistencialeccion.virtual = vVirtual
                                            asistencialeccion.virtual_fecha = asistencias.virtual_fecha
                                            asistencialeccion.virtual_hora = asistencias.virtual_hora
                                            asistencialeccion.ip_private = asistencias.ip_private
                                            asistencialeccion.ip_public = asistencias.ip_public
                                            asistencialeccion.browser = asistencias.browser
                                            asistencialeccion.ops = asistencias.ops
                                            asistencialeccion.screen_size = asistencias.screen_size
                                            asistencialeccion.save()
                                        materiaasignada = asistencias.materiaasignada
                                        if variable_valor('ACTUALIZA_ASISTENCIA'):
                                            if not materiaasignada.sinasistencia:
                                                materiaasignadaactualiza.append(materiaasignada.id)
                                                # ActualizaAsistencia(materiaasignada.id)

                                        if ePeriodoAcademia:
                                            if ePeriodoAcademia.utiliza_asistencia_redis and (ePeriodoAcademia.es_virtual() or ePeriodoAcademia.es_hibrida()):
                                                redis = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD)
                                                key_alumno = f'{encrypt(leccion.clase_id)}{encrypt(turno.id)}{encrypt(materiaasignada.matricula.inscripcion.persona.usuario_id)}{encrypt(leccion.clase.dia)}{leccion.fecha.strftime("%d%m%Y")}'
                                                aData = {
                                                    'user_id': materiaasignada.matricula.inscripcion.persona.usuario_id,
                                                    'clase_id': leccion.clase_id,
                                                    'dia': leccion.clase.dia,
                                                    'turno_id': turno.id,
                                                    "fecha": leccion.fecha.strftime("%d-%m-%Y"),
                                                    # "noti_id": noti.id,
                                                    "leccion_id": leccion.id,
                                                    "leccion_grupo_id": lecciongrupo.id,
                                                }
                                                # d = datetime.now()
                                                d = leccion.fecha
                                                d2 = datetime(d.year, d.month, d.day, turno.comienza.hour, turno.comienza.minute)
                                                time_life_token = (time.mktime((datetime(d.year, d.month, d.day, turno.termina.hour, turno.termina.minute)).timetuple()) - time.mktime(d2.timetuple()))
                                                value = json.dumps(aData)
                                                redis.setex(key_alumno, int(time_life_token), value)

                                        # materiaasignada.actualiza_estado()
                                    # guardar temas de silabo
                                    for tema in TemaAsistencia.objects.filter(leccion_id=leccionanterior.id, status=True):
                                        temaasistencia = TemaAsistencia(leccion_id=leccion.id, tema=tema.tema, fecha=datetime.now().date())
                                        temaasistencia.save()
                                        for subtema in SubTemaAsistencia.objects.filter(tema_id=tema.id):
                                            subtemaasistencia = SubTemaAsistencia(tema_id=temaasistencia.id, subtema=subtema.subtema, fecha=datetime.now().date())
                                            subtemaasistencia.save()


                                lecciongrupo.save()
                                print(" ABIERTA CLASES CONTINUAS\r")
                            except Exception as ex:
                                transaction.set_rollback(True)
                                print(f"Error al abrir la lección grupo")
        else:
            print("NO CUMPLE CONDICIONALES\r")

    with transaction.atomic():
        try:
            if materiaasignadaactualiza:
                for materiaasignada_id in materiaasignadaactualiza:
                    ActualizaAsistencia(materiaasignada_id)
        except Exception as ex:
            transaction.set_rollback(True)
            print(f"Error al actualizar las asistencias")

exitFlag = 0


class myThread (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name + "\r")
        process_data(self.name, self.q)
        print("Exiting " + self.name + "\r")


def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            data = q.get()
            queueLock.release()
            print("%s PROCESANDO %s" % (threadName, data.id))
            cerrar(data)
        else:
            queueLock.release()



threadList = ["Thread-"+str(id) for id in range(0, HILOS_MAXIMOS)]
nameList = range(0, 1000)
queueLock = threading.Lock()
workQueue = queue.Queue(LeccionGrupo.objects.filter(abierta=True, solicitada=False).count())
threads = []
threadID = 1

# Create new threads
for tName in threadList:
    thread = myThread(threadID, tName, workQueue)
    thread.start()
    threads.append(thread)
    threadID += 1

# Fill the queue
queueLock.acquire()
if CLASES_HORARIO_ESTRICTO and CLASES_CIERRE_AUTOMATICA:
    print("CERRANDO CLASES ABIERTAS DESPUES DE TIEMPO " + datetime.now().__str__() + "\r")
    for leccciong in LeccionGrupo.objects.filter(abierta=True, solicitada=False):
        workQueue.put(leccciong)
else:
    print("HORARIO NO ESTRICTO")
queueLock.release()

# Wait for queue to empty
while not workQueue.empty():
    pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
    t.join()
print("HECHO" + datetime.now().__str__())
