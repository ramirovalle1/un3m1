#!/usr/bin/env python
import os
import sys

csv_filepathname3 = "problemas2021_corregido_g6.csv"
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
import sys
from datetime import datetime

from django.db import transaction

from sga.funciones import lista_mejores_promedio_beca_v3, asignar_orden_portipo_beca, listado_incripciones_reconocimiento_academico, lista_discapacitado_beca, lista_deportista_beca, lista_migrante_exterior_beca, lista_etnia_beca, lista_gruposocioeconomico_beca
from sga.models import BecaTipo, Inscripcion, PreInscripcionBeca, Periodo, Matricula
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


def generar(periodoactual, periodoanterior):
    with transaction.atomic():
        try:
            becatipos = BecaTipo.objects.filter(status=True, vigente=True)
            ID_PRIMER_NIVEL = 16
            ID_MEJOR_PROMEDIO = 17
            ID_DISCAPACIDAD = 19
            ID_DEPORTISTA = 20
            ID_EXTERIOR_MIGRANTE = 22
            ID_ETNIA = 21
            ID_GRUPO_VULNERABLE = 18
            EXCLUDES = []

            """LISTADO DE LOS MEJORES PROMEDIOS POR MALLA"""
            mejores = lista_mejores_promedio_beca_v3(periodoactual, periodoanterior=periodoanterior, limit=1)
            if not mejores:
                raise NameError('la función de generar Listados de Beca de Alto rendimiento fallo')
            inscripciones_exclusiones = Inscripcion.objects.filter(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual)).values_list('id', flat=True)
            if inscripciones_exclusiones:
                mejores = [inscripcion for inscripcion in mejores if not inscripcion.pk in list(inscripciones_exclusiones)]
            for i, inscripcion in enumerate(mejores):
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promediototal,
                                                        desviacion_estandar=inscripcion.desviacion_estandar,
                                                        promedio_carrera=inscripcion.promedio_carrera,
                                                        becatipo=becatipos.filter(pk=ID_MEJOR_PROMEDIO).first(),
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()

            asignar_orden_portipo_beca(ID_MEJOR_PROMEDIO, periodoactual)
            #Asignar Orden de por promedio
            EXCLUDES.extend([inscripcion.pk for inscripcion in mejores])
            """LISTADO DE INSCRIPCIONES DE PRIMER NIVEL CON RECONOCIMIENTO ACADEMICO"""
            # destacadosprimernivel = listado_incripciones_reconocimiento_academico(periodoactual, excludes=EXCLUDES)
            # inscripciones_destacadosprimernivel = destacadosprimernivel#.exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
            #
            # for inscripcion in inscripciones_destacadosprimernivel:
            #     preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
            #     if not preinscripcion:
            #         preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
            #                                             promedio=inscripcion.promedio,
            #                                             becatipo=becatipos.filter(pk=ID_PRIMER_NIVEL).first(),
            #                                             periodo=periodoactual,
            #                                             fecha=datetime.now().date())
            #         preinscripcion.save()
            #         preinscripcion.generar_requistosbecas()
            #
            # asignar_orden_portipo_beca(ID_PRIMER_NIVEL, periodoactual)
            # EXCLUDES.extend(destacadosprimernivel)

            """LISTADO DE DISCAPACITADOS EXCLUYENDO A LOS DE MEJORES PROMEDIOS"""
            discapacitados = lista_discapacitado_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, excludes=EXCLUDES)
            inscripciones_discapacitados = Inscripcion.objects.filter(pk__in=discapacitados) #.exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
            # actualizar_discapacitados = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_DISCAPACIDAD).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_discapacitados)
            # if DEBUG:
            #     actualizar_discapacitados.delete()

            for inscripcion in inscripciones_discapacitados:
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                perfilinscripcion = inscripcion.persona.perfilinscripcion_set.filter(status=True).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promedio,
                                                        becatipo=becatipos.filter(pk=ID_DISCAPACIDAD).first(),
                                                        tipodiscapacidad=perfilinscripcion.tipodiscapacidad if perfilinscripcion else None,
                                                        porcientodiscapacidad=perfilinscripcion.porcientodiscapacidad if perfilinscripcion else None,
                                                        carnetdiscapacidad=perfilinscripcion.carnetdiscapacidad if perfilinscripcion else None,
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()

            asignar_orden_portipo_beca(ID_DISCAPACIDAD, periodoactual)
            EXCLUDES.extend(discapacitados)
            """LISTADO DE DEPORTISTAS EXCLUYENDO A DISCAPACITADOS Y LOS DE MEJORES PROMEDIOS"""
            deportistas = lista_deportista_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, excludes=EXCLUDES)
            inscripciones_deportistas = Inscripcion.objects.filter(pk__in=deportistas)#.exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
            # actualizar_deportistas = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_DEPORTISTA).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_deportistas)
            # if DEBUG:
            #     actualizar_deportistas.delete()
            for inscripcion in inscripciones_deportistas:
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promedio,
                                                        becatipo=becatipos.filter(pk=ID_DEPORTISTA).first(),
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()
            asignar_orden_portipo_beca(ID_DEPORTISTA, periodoactual)
            EXCLUDES.extend(deportistas)
            """LISTADO DE PERSONAS EN EL EXTRANJERO EXCLUYENDO A DISCAPACITADOS, DEPORTISTAS Y LOS DE MEJORES PROMEDIOS"""
            migrantes = lista_migrante_exterior_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, excludes=EXCLUDES)
            inscripciones_migrantes = Inscripcion.objects.filter(pk__in=migrantes)#.exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
            # actualizar_migrantes = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_EXTERIOR_MIGRANTE).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_migrantes)
            # if DEBUG:
            #     actualizar_migrantes.delete()
            for inscripcion in inscripciones_migrantes:
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promedio,
                                                        becatipo=becatipos.filter(pk=ID_EXTERIOR_MIGRANTE).first(),
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()
            asignar_orden_portipo_beca(ID_EXTERIOR_MIGRANTE, periodoactual)
            EXCLUDES.extend(migrantes)
            """LISTADO DE PERSONAS ETNIA EXCLUYENDO EXTRANJERO, MIGRANTES, DISCAPACITADOS, DEPORTISTAS Y LOS DE MEJORES PROMEDIOS"""
            etnias = lista_etnia_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, excludes=EXCLUDES)
            inscripciones_etnias = Inscripcion.objects.filter(pk__in=etnias)#.exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
            # actualizar_etnias = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_ETNIA).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_etnias)
            # if DEBUG:
            #     actualizar_etnias.delete()
            for inscripcion in inscripciones_etnias:
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                perfilinscripcion = inscripcion.persona.perfilinscripcion_set.filter(status=True).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promedio,
                                                        becatipo=becatipos.filter(pk=ID_ETNIA).first(),
                                                        raza=perfilinscripcion.raza if perfilinscripcion else None,
                                                        periodo=periodoactual ,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()
            asignar_orden_portipo_beca(ID_ETNIA, periodoactual)
            EXCLUDES.extend(etnias)

            # pruebas = PreInscripcionBeca.objects.filter(periodo=periodo).exclude(becatipo=becatipos.filter(pk=ID_GRUPO_VULNERABLE).first())
            # EXCLUDES.extend(list(pruebas.values_list('inscripcion_id', flat=True).distinct()))
            """LISTADO DE PERSONAS DE GRUPO VULNERABLE EXCLUYENDO ETNIA, EXTRANJERO, MIGRANTES, DISCAPACITADOS, DEPORTISTAS Y LOS DE MEJORES PROMEDIOS"""
            grupo = []
            for grupo_id in [4, 5]:
                grupo.extend(lista_gruposocioeconomico_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, tipogrupo_id=grupo_id, excludes=EXCLUDES, limit=100))
            # lit_ex = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual, becatipo_id=17).values_list('id',flat=True)
            inscripciones_grupo = grupo#[g for g in grupo if not g.pk in lit_ex ] #Inscripcion.objects.filter(pk__in=[inscripcion.pk for inscripcion in grupo])

            # actualizar_grupo = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_GRUPO_VULNERABLE).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_grupo)
            # if DEBUG:
            #     actualizar_grupo.delete()
            for inscripcion in inscripciones_grupo:
                preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
                if not preinscripcion:
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promediototal,
                                                        becatipo=becatipos.filter(pk=ID_GRUPO_VULNERABLE).first(),
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()
            asignar_orden_portipo_beca(ID_GRUPO_VULNERABLE, periodoactual)
            preinscripciones_sin_requisitos = PreInscripcionBeca.objects.filter(periodo=periodoactual, preinscripcionbecarequisito__isnull=True)
            for preinscripcionbeca in preinscripciones_sin_requisitos:
                preinscripcionbeca.generar_requistosbecas()

            error = False

        except Exception as ex:
            transaction.set_rollback(True)
            print(ex)
            err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
            error = True
            mensaje_ex = f'{err} {ex.__str__()}'


def generar_primernivel(periodoactual, periodoanterior):
    becatipos = BecaTipo.objects.filter(status=True, vigente=True)
    ID_PRIMER_NIVEL = 16
    EXCLUDES = []
    """LISTADO DE INSCRIPCIONES DE PRIMER NIVEL CON RECONOCIMIENTO ACADEMICO"""
    # PreInscripcionBeca.objects.filter(becatipo_id=16, periodo_id=periodoanterior).delete()
    # eMatriculas_1 = Matricula.objects.filter(status=True, nivel__periodo=periodoactual,
    #                                          estado_matricula__in=[2, 3],
    #                                          matriculagruposocioeconomico__tipomatricula=1,
    #                                          nivelmalla__orden__gte=2,
    #                                          retiradomatricula=False
    #                                          )
    eMatriculas_1 = Matricula.objects.filter(status=True, nivel__periodo=periodoactual,
                                             estado_matricula__in=[2, 3],
                                             matriculagruposocioeconomico__tipomatricula=1,
                                             nivelmalla__orden=1,
                                             retiradomatricula=False,
                                             bloqueomatricula=False,
                                             materiaasignada__estado_id=3
                                             )
    # eMatriculas_2 = Matricula.objects.filter(status=True,
    #                                          nivel__periodo=periodoanterior,
    #                                          retiradomatricula=False,
    #                                          estado_matricula__in=[2, 3],
    #                                          matriculagruposocioeconomico__tipomatricula=1,
    #                                          materiaasignada__estado_id=1,
    #                                          nivelmalla__orden=1).exclude(Q(materiaasignada__retiramateria=True) | Q(materiaasignada__estado_id__gt=1))

    # eMatriculas_2 = eMatriculas_2.filter(inscripcion_id__in=eMatriculas_1.values_list("inscripcion__id", flat=True))
    # eInscripciones = Inscripcion.objects.filter(persona__titulacion__detalletitulacionbachiller__reconocimientoacademico__isnull=False,
    #                                             persona__titulacion__detalletitulacionbachiller__anioinicioperiodograduacion__isnull=False,
    #                                             persona__titulacion__detalletitulacionbachiller__aniofinperiodograduacion__isnull=False,
    #                                             persona__titulacion__detalletitulacionbachiller__calificacion__gte=9,
    #                                             persona__titulacion__detalletitulacionbachiller__status=True, pk__in=eMatriculas_2.values_list("inscripcion__id", flat=True))
    eInscripciones = Inscripcion.objects.filter(persona__titulacion__detalletitulacionbachiller__reconocimientoacademico__isnull=False,
                                                persona__titulacion__detalletitulacionbachiller__anioinicioperiodograduacion__isnull=False,
                                                persona__titulacion__detalletitulacionbachiller__aniofinperiodograduacion__isnull=False,
                                                persona__titulacion__detalletitulacionbachiller__calificacion__gte=9,
                                                persona__titulacion__detalletitulacionbachiller__status=True, pk__in=eMatriculas_1.values_list("inscripcion__id", flat=True))
    # inscripcionesactuales = Inscripcion.objects.values_list('id',flat=True).filter(
    #     persona__titulacion__detalletitulacionbachiller__reconocimientoacademico__isnull=False,
    #     persona__titulacion__detalletitulacionbachiller__anioinicioperiodograduacion__isnull=False,
    #     persona__titulacion__detalletitulacionbachiller__aniofinperiodograduacion__isnull=False,
    #     #persona__titulacion__detalletitulacionbachiller__calificacion__gte=9,
    #     persona__titulacion__detalletitulacionbachiller__status=True,
    #     status=True,
    #     matricula__nivel__periodo=periodoactual,
    #     matricula__status=True,
    #     matricula__estado_matricula__in=[2, 3],
    #     matricula__matriculagruposocioeconomico__tipomatricula=1,
    #     matricula__nivelmalla__orden__gte=2).distinct()
    #
    # inscripcionesanteriores = Inscripcion.objects.filter(
    #     persona__titulacion__detalletitulacionbachiller__reconocimientoacademico__isnull=False,
    #     persona__titulacion__detalletitulacionbachiller__anioinicioperiodograduacion__isnull=False,
    #     persona__titulacion__detalletitulacionbachiller__aniofinperiodograduacion__isnull=False,
    #     persona__titulacion__detalletitulacionbachiller__calificacion__gte=9,
    #     persona__titulacion__detalletitulacionbachiller__status=True,
    #     status=True,
    #     matricula__nivel__periodo=periodoanterior,
    #     matricula__estado_matricula__in=[2, 3],
    #     matricula__status=True,
    #     matricula__matriculagruposocioeconomico__tipomatricula=1,
    #     matricula__nivelmalla__orden=1,
    #     id__in=inscripcionesactuales).exclude(Q(matricula__materiaasignada__estado__gt=1) | Q(matricula__materiaasignada__retiramateria=True) | Q(matricula__materiaasignada__cerrado=False)).distinct()

    ##inscripciones = inscripcionesanteriores.exclude(pk__in=excludes) if excludes else inscripcionesanteriores
    listado_inscripciones = []
    for eInscripcion in eInscripciones:
        if eInscripcion.persona.es_ecuatoriano() and not eInscripcion.tiene_materias_reprobados_preinscripcionbeca() and not eInscripcion.tiene_modulos_ingles_reprobados_preinscripcionbeca() and not eInscripcion.tiene_modulos_computacion_reprobados_preinscripcionbeca():
            listado_inscripciones.append(eInscripcion)
            print(u"Reconocimiemto Academico Primer Nivel: %s, estudiante: %s" % (eInscripcion.carrera, eInscripcion.persona))
    #destacadosprimernivel = listado_incripciones_reconocimiento_academico(periodoactual, periodoanterior, excludes=EXCLUDES)
    # inscripciones_destacadosprimernivel = inscripcionesanteriores  # .exclude(persona_id__in=PreInscripcionBeca.objects.values("inscripcion__persona_id").filter(periodo=periodoactual))
    # actualizar_destacadosprimernivel = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_PRIMER_NIVEL).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_destacadosprimernivel)
    # if DEBUG:
    #     actualizar_destacadosprimernivel.delete()

    for inscripcion in listado_inscripciones:
        # preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoanterior).first()
        preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).first()
        if not preinscripcion:
            preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                promedio=inscripcion.promedio,
                                                becatipo=becatipos.filter(pk=ID_PRIMER_NIVEL).first(),
                                                # periodo=periodoanterior,
                                                periodo=periodoactual,
                                                fecha=datetime.now().date())
            preinscripcion.save()
            preinscripcion.generar_requistosbecas()

    # asignar_orden_portipo_beca(ID_PRIMER_NIVEL, periodoanterior)
    asignar_orden_portipo_beca(ID_PRIMER_NIVEL, periodoactual)
    #EXCLUDES.extend(destacadosprimernivel)


def generate_precandidatos_beca(periodoactual, periodoanterior):
    error = False
    mensaje_ex = None
    with transaction.atomic():
        try:
            becatipos = BecaTipo.objects.filter(status=True, vigente=True)
            ID_GRUPO_VULNERABLE = 18
            EXCLUDES = []
            ePreInscripcionBecas = PreInscripcionBeca.objects.filter(periodo=periodoactual)
            EXCLUDES.extend(list(ePreInscripcionBecas.values_list("inscripcion__id", flat=True)))
            grupo = []
            for grupo_id in [4, 5]:
                grupo.extend(lista_gruposocioeconomico_beca(periodoactual=periodoactual, periodoanterior=periodoanterior, tipogrupo_id=grupo_id, excludes=EXCLUDES, limit=15))
            # inscripciones_grupo = Inscripcion.objects.filter(pk__in=grupo).exclude(persona_id__in=ePreInscripcionBecas.values("inscripcion__persona_id"))
            # actualizar_grupo = PreInscripcionBeca.objects.filter(becatipo=becatipos.filter(pk=ID_GRUPO_VULNERABLE).first(), periodo=periodoactual).exclude(inscripcion__in=inscripciones_grupo)
            # if DEBUG:
            #     actualizar_grupo.delete()
            inscripciones_grupo = grupo
            total = len(inscripciones_grupo)
            print(f"Total de inscripciones a registar {total}")
            contador = 0
            contadorNew = 0
            for inscripcion in inscripciones_grupo:
                contador += 1
                if not PreInscripcionBeca.objects.filter(inscripcion=inscripcion, periodo=periodoactual).exists():
                    preinscripcion = PreInscripcionBeca(inscripcion=inscripcion,
                                                        promedio=inscripcion.promediototal,
                                                        becatipo=becatipos.filter(pk=ID_GRUPO_VULNERABLE).first(),
                                                        periodo=periodoactual,
                                                        fecha=datetime.now().date())
                    preinscripcion.save()
                    preinscripcion.generar_requistosbecas()
                    contadorNew += 1
                    print(f"({total}/{contador}) Inscripcion: {inscripcion.__str__()} ->>> SE CREO")
                else:
                    print(f"({total}/{contador}) Inscripcion: {inscripcion.__str__()} ->>> NO SE CREO --YA EXISTE--")
            asignar_orden_portipo_beca(ID_GRUPO_VULNERABLE, periodoactual)
            error = False
            print(f"Finaliza total que se crearon {contadorNew}")
        except Exception as ex:
            transaction.set_rollback(True)
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            error = True
            mensaje_ex = ex.__str__()


periodoactual = Periodo.objects.get(status=True, id=153)
periodoanterior = Periodo.objects.get(status=True, id=126)
print(f"EMPIEZA PROCESO DEL PERIODO {periodoactual.__str__()}")
ePreInscripcionBecas = PreInscripcionBeca.objects.filter(periodo=periodoactual)
print(f"Data a eliminar {len(ePreInscripcionBecas)}")
ePreInscripcionBecas.delete()
generar(periodoactual, periodoanterior)
# #

# periodoactual = Periodo.objects.get(status=True, id=126)
# periodoanterior = Periodo.objects.get(status=True, id=119)
# print(f"EMPIEZA PROCESO DEL PERIODO {periodoactual.__str__()}")
# ePreInscripcionBecas = PreInscripcionBeca.objects.filter(periodo=periodoactual)
# print(f"Data a eliminar {len(ePreInscripcionBecas)}")
# generate_precandidatos_beca(periodoactual, periodoanterior)
# ePreInscripcionBecas.delete()
# generar(periodoactual, periodoanterior)

# PreInscripcionBecas = PreInscripcionBeca.objects.filter(periodo=periodoactual,
#                                                         becatipo_id=19,
#                                                         promedio=0)
#
# print(f"TOTAL: {len(PreInscripcionBecas.values('id'))}")




# periodoactual = Periodo.objects.get(status=True, id=126)
# periodoanterior = Periodo.objects.get(status=True, id=119)
# generar_primernivel(periodoactual, periodoanterior)


#ordenar becas
# ID_GRUPO_VULNERABLE = 18
# periodoactual = Periodo.objects.get(pk=126)
# def ordenar_grupo_vulnerable(gupo_vulnerable, periodoactual):
#     asignar_orden_portipo_beca(gupo_vulnerable, periodoactual)
#
# ordenar_grupo_vulnerable(ID_GRUPO_VULNERABLE, periodoactual)
