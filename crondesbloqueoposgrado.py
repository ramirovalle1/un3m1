#!/usr/bin/env python

import os


from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


from sga.models import *
from sagest.models import *

def desbloquear():
    print(".:: Proceso de desbloqueo Matriculas Posgrado y Acceso Moodle ::.")
    hoy = datetime.now().date()
    cnmoodle = connections['moodle_pos'].cursor()

    listamatriculas = Rubro.objects.values_list('matricula_id').filter(matricula__bloqueomatricula=True, tipo__tiporubro=1, status=True).distinct()
    total = 0
    for lismatri in listamatriculas:
        matricula = Matricula.objects.get(pk=lismatri[0])

        print("Revisando Matricula ID:", matricula)

        rubrosvencidos = matricula.rubro_set.filter(fechavence__lt=hoy, matricula__isnull=False, tipo__tiporubro=1, cancelado=False, status=True).count()

        if rubrosvencidos < 3:
            matricula.bloqueomatricula = False
            matricula.save()

            # Consulto usuario de moodle
            usermoodle = matricula.inscripcion.persona.idusermoodleposgrado

            if usermoodle != 0:
                # Consulta en mooc_user
                sql = """Select id, username From mooc_user Where id=%s""" % (usermoodle)
                cnmoodle.execute(sql)
                registro = cnmoodle.fetchall()
                idusuario = registro[0][0]
                username = registro[0][1]

                # Asignar estado deleted = 0 para que pueda acceder al aula virtual
                sql = """Update mooc_user Set deleted=0 Where id=%s""" % (idusuario)
                cnmoodle.execute(sql)

            total += 1

    cnmoodle.close()

    print("Total desbloqueados: ", total)
    print("Proceso terminado...")


def desbloqueo_individual():
    cnmoodle = connections['moodle_pos'].cursor()

    idmatricula = 300617

    matricula = Matricula.objects.get(pk=idmatricula)

    print(matricula)

    matricula.bloqueomatricula = False
    matricula.save()
    print("Matrícula desbloqueada")

    # Consulto usuario de moodle
    usermoodle = matricula.inscripcion.persona.idusermoodleposgrado

    if usermoodle != 0:
        # Consulta en mooc_user
        sql = """Select id, username From mooc_user Where id=%s""" % (usermoodle)
        cnmoodle.execute(sql)
        registro = cnmoodle.fetchall()
        idusuario = registro[0][0]
        username = registro[0][1]

        # Asignar estado deleted = 0 para que pueda acceder al aula virtual
        sql = """Update mooc_user Set deleted=0 Where id=%s""" % (idusuario)
        cnmoodle.execute(sql)

        print("Acceso a moodle desbloqueado")

    cnmoodle.close()

# print("Hora actual:", datetime.now().time())
# if datetime.now().time() <= datetime.strptime('20:00:00', '%H:%M:%S').time():
#     desbloquear()
# else:
#     print("El proceso está disponible para su ejecución hasta las 22:00:00")

desbloqueo_individual()