import json
import os
import sys
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sagest.models import *
import sys
import openpyxl
from urllib.request import urlopen, Request
import os

try:
    persona = Persona.objects.get(pk=29898)
    miarchivo = openpyxl.load_workbook("modulos_ingles.xlsx")
    # miarchivo = openpyxl.load_workbook("ajuste.xlsx")
    lista = miarchivo.get_sheet_by_name('FINAL')
    totallista = lista.rows
    a = 0
    # educacion basica en linea
    for filas in totallista:
        a += 1
        if a > 1:
            id_materiaasignada = filas[0].value
            idcursomoodle = filas[1].value
            if not id_materiaasignada:
                break
            materiaasignada = MateriaAsignada.objects.get(id=id_materiaasignada)
            url = 'https://upei.buckcenter.edu.ec/usernamecoursetograde.php?username=%s&curso=%s' % (materiaasignada.matricula.inscripcion.persona.identificacion(), idcursomoodle)
            req = Request(url)
            response = urlopen(req)
            result = json.loads(response.read().decode())
            nota = None
            try:
                nota = null_to_decimal(result['nota'], 0)
            except:
                if result['nota'] == '-' or result['nota'] == None:
                    nota = 0
            if nota:
                if (nota != materiaasignada.notafinal and type(nota) in [int, float]) or nota == 0:
                    campo = materiaasignada.campo('EX')
                    actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,calificacion=nota)
                    auditorianotas.save()
                    materiaasignada.importa_nota = True
                    materiaasignada.cerrado = True
                    materiaasignada.fechacierre = datetime.now().date()
                    materiaasignada.save()
                    d = locals()
                    exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                    d['calculo_modelo_evaluativo'](materiaasignada)
                    materiaasignada.cierre_materia_asignada()
                    print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))



except Exception as ex:
    print('error: %s' % ex)
    noti = Notificacion(titulo='Error',
                        cuerpo='Ha ocurrido un error {} - Error en la linea {}'.format(
                            ex, sys.exc_info()[-1].tb_lineno),
                        destinatario_id=29898, url="",
                        prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1),
                        tipo=2, en_proceso=False, error=True)
    noti.save()
