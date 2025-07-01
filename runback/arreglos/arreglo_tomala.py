import os
import sys
import xlsxwriter
import xlwt
import openpyxl
from django.db import transaction
from datetime import datetime, timedelta
import math
from urllib.request import urlopen, Request
from django.http import HttpResponse
from xlwt import *

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
from settings import UTILIZA_NIVEL0_PROPEDEUTICO, MATRICULACION_LIBRE, HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, \
    MATRICULACION_POR_NIVEL, UTILIZA_GRUPOS_ALUMNOS, UTILIZA_GRATUIDADES,PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from matricula.models import SolicitudMatriculaEspecial, EstadoMatriculaEspecial


def cargar():
    id_estado=[2,3,7]
    solicitante=SolicitudMatriculaEspecial.objects.filter(status=True,periodo=177, estado__in=id_estado)#.values("inscripcion_id").distinct()
    for persona in solicitante:
        print(persona.inscripcion.persona)
        if MATRICULACION_LIBRE:
            hoy = datetime.now().date()
            nivelaux = Nivel.objects.filter(nivellibrecoordinacion__coordinacion__carrera=persona.inscripcion.carrera,
                                    nivellibrecoordinacion__coordinacion__sede=persona.inscripcion.sede, modalidad=persona.inscripcion.modalidad, cerrado=False,
                                    fin__gte=hoy, periodo=177)

            if nivelaux.exists():
                tipo_matricula_ri=3
                nivela = Nivel.objects.filter(nivellibrecoordinacion__coordinacion__carrera=persona.inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=persona.inscripcion.sede, modalidad=persona.inscripcion.modalidad, cerrado=False, fin__gte=hoy, periodo=177).order_by('-fin')[0]
                nivel = Nivel.objects.get(pk=nivela.id)
                inscripcion=Inscripcion.objects.get(pk=persona.inscripcion.id)
                if inscripcion.estado_gratuidad == 2:
                    cobro = 3
                try:
                    if UTILIZA_GRATUIDADES:
                        if not inscripcion.persona.tiene_otro_titulo:
                            if inscripcion.estado_gratuidad == 1 or inscripcion.estado_gratuidad == 2:
                                if inscripcion.estado_gratuidad == 2:
                                    cobro = 2
                                else:
                                    cobro = 2
                            else:
                                cobro = 3
                        else:
                            cobro = 3;
                    #persona = inscripcion.persona
                    mispracticas = []
                    tipo_matricula_ri = 3
            #         seleccion = []
            #         materias = Materia.objects.filter(id__in=seleccion, status=True)
            # # MATERIAS PRACTICAS
            #         listaprofemateriaid_singrupo = []
            #         listaprofemateriaid_congrupo = []
            #         listagrupoprofesorid = []
            #         for x in mispracticas:
            #             if not int(x[1]) > 0:
            #                 listaprofemateriaid_singrupo.append(int(x[0]))
            #             else:
            #                 listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
            #                 listagrupoprofesorid.append(int(x[1]))
            #         profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo)
            #         grupoprofesormateria = GruposProfesorMateria.objects.filter(id__in=listagrupoprofesorid)
            #
            #
            #     # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            #         if inscripcion.carrera.id in [1, 3]:
            #             totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=profesoresmateriassingrupo.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormateria.values('profesormateria__materia__id')).count()
            #             if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
            #                 print({"result": "bad", "mensaje": "Falta de seleccionar horario de practicas"})
            #
            #
            #     # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
            #         materiasasistir = []
            #         for m in materias:
            #             if not inscripcion.sin_asistencia(m.asignatura):
            #                 materiasasistir.append(m)
                # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO

                    hoy = convertir_fecha('07-04-2023')
                    if not inscripcion.matriculado_periodo(nivel.periodo):
                        with transaction.atomic():
                            matricula = Matricula(inscripcion=inscripcion,

                                          nivel=nivel,
                                          pago=False,
                                          iece=False,
                                          becado=False,
                                          porcientobeca=0,
                                          fecha=hoy,
                                          hora='12:38:50',
                                          fechatope=hoy,
                                          termino=True,
                                          fechatermino=hoy)

                            matricula.save()
                            matricula.confirmar_matricula()

                            codigoitinerario = 0
                            matricula.actualizar_horas_creditos()
                            Estado_matricula=EstadoMatriculaEspecial.objects.get(pk=4)
                            persona.estado=Estado_matricula
                            persona.save()
                            if not inscripcion.itinerario or inscripcion.itinerario < 1:
                                inscripcion.itinerario = codigoitinerario
                                inscripcion.save()

                        with transaction.atomic():
                            if int(cobro) > 0:
                                if matricula.inscripcion.mi_coordinacion().id != 9:
                                    matricula.agregacion_aux(0)
                            matricula.actualiza_matricula()
                            matricula.inscripcion.actualiza_estado_matricula()
                            matricula.grupo_socio_economico(tipo_matricula_ri)
                            matricula.calcula_nivel()
                        valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))

                        descripcionarancel = ''
                        valorarancel = ''
                        if matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).exists():
                            ra = matricula.rubro_set.get(tipo_id=RUBRO_ARANCEL)
                            descripcionarancel = ra.nombre
                            valorarancel = str(ra.valortotal)

                            matricula.aranceldiferido = 2
                            matricula.save()
                            print("matriculado correctamente")
                            print(valorpagar)
                            print(valorarancel)
                        ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)
                    else:
                        print("ya estaba matriculado...")
                except Exception as ex:
                    print(ex)
                    print("error al matricular")
cargar()




# import os
# import sys
# import xlsxwriter
# import xlwt
# import openpyxl
# from xlwt import *
#
# # SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
# YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# # print(f"YOUR_PATH: {YOUR_PATH}")
# SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
# SITE_ROOT = os.path.join(SITE_ROOT, '')
# # print(f"SITE_ROOT: {SITE_ROOT}")
# your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# # print(f"your_djangoproject_home: {your_djangoproject_home}")
# sys.path.append(your_djangoproject_home)
#
# from django.core.wsgi import get_wsgi_application
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# application = get_wsgi_application()
#
# from django.http import HttpResponse
# from settings import MEDIA_ROOT, BASE_DIR
# from xlwt import easyxf, XFStyle
# from sga.adm_criteriosactividadesdocente import asistencia_tutoria
# from inno.models import *
# from sga.models import *
# from sagest.models import *
# from Moodle_Funciones import buscarQuiz, estadoQuizIndividual, accesoQuizIndividual
#
#
#
# def cambio_pass():
#     for persona in Persona.objects.filter(status=True):
#         if not persona.perfilusuario_set.filter(Q(status=True), Q(empleador_id__isnull=False)):
#             print(persona, persona.usuario)
#             persona.clave_cambiada()
#             if not persona.cambioclavepersona_set.exists():
#                 persona.cambiar_clave()
#     print('FIN')
#
#
# cambio_pass()

