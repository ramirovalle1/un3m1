import os
import sys

from django.db import transaction
from django.db.models import Q

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sagest.models import DetalleConstatacionFisicaActivoTecnologico, InformeActivoBaja
from sga.models import Materia, Inscripcion, Matricula, Modulo, miinstitucion


def copiar_migraciones():
    import os
    import shutil

    ruta_base = "D:/git/academico"
    ruta_destino = "E:/academico"

    for root, dirs, files in os.walk(ruta_base):
        if "migrations" in dirs:
            nombre_carpeta = os.path.basename(root)
            ruta_completa_destino = os.path.join(ruta_destino, f"{nombre_carpeta}")
            ruta_completa_migrations = os.path.join(ruta_completa_destino, f"migrations")
            try:
                shutil.copytree(os.path.join(root, "migrations"), ruta_completa_migrations)
                print(f"Copia creada en {ruta_completa_migrations}")
            except FileExistsError:
                print(f"La carpeta {ruta_completa_destino} ya existe.")
            except Exception as e:
                print(f"Error al copiar {nombre_carpeta}: {e}")
def modulossga():
    # mis = ModuloCategorias.objects.create(nombre=f"General", prioridad=1)
    # qsmodulos = Modulo.objects.all()

    #ACTIVOS
    qsmodulos = Modulo.objects.filter(id__in=[491,
                                                122,
                                                509,
                                                128,
                                                522,
                                                451,
                                                488,
                                                492,
                                                462,
                                                487,
                                                129,
                                                247,
                                                127,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([8])
        mod.save()

    #TALENTO HUMANO
    qsmodulos = Modulo.objects.filter(id__in=[208,
                                                53,
                                                263,
                                                259,
                                                338,
                                                348,
                                                252,
                                                131,
                                                308,
                                                150,
                                                113,
                                                155,
                                                16,
                                                422,
                                                134,
                                                133,
                                                125,
                                                264,
                                                203,
                                                202,
                                                168,
                                                123,
                                                421,
                                                475,
                                                262,
                                                121,
                                                398,
                                                130,
                                                135,
                                                347,
                                                396,
                                                238,
                                                233,
                                                 ])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([9])
        mod.save()

    # FINANCIERO
    qsmodulos = Modulo.objects.filter(id__in=[199,
                                                354,
                                                365,
                                                214,
                                                329,
                                                165,
                                                395,
                                                194,
                                                43,
                                                108,
                                                189,
                                                181,
                                                188,
                                                167,
                                                196,
                                                187,
                                                173,
                                                42,
                                                40,
                                                375,
                                                198,
                                                178,
                                                521,
                                                163,
                                                204,
                                                298,
                                                171,
                                                200,
                                                110,
                                                51,
                                                378,
                                                41,
                                                166,
                                                182,
                                                217,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([10])
        mod.save()

    #BODEGA
    qsmodulos = Modulo.objects.filter(id__in=[157,
                                                458,
                                                111,
                                                112,
                                                206,
                                                109,
                                                393,
                                                205,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([11])
        mod.save()

    #OBRAS
    qsmodulos = Modulo.objects.filter(id__in=[172,
                                                323,
                                                177,
                                                149,
                                                148,
                                                ])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([12])
        mod.save()

    # PLANIFICACIÓN INSTITUCIONAL
    qsmodulos = Modulo.objects.filter(id__in=[333,
                                                261,
                                                147,
                                                339,
                                                146,
                                                174,
                                                141,
                                                138,
                                                142,
                                                137,
                                                145,
                                                144,
                                                175,
                                                143,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([13])
        mod.save()

    # SISTEMA
    qsmodulos = Modulo.objects.filter(id__in=[401,
                                                515,
                                                81,
                                                156,
                                                473,
                                                503,
                                                391,
                                                516,
                                                310,
                                                502,
                                                ])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([14])
        mod.save()

    #ADMINISTRATIVOS
    qsmodulos = Modulo.objects.filter(id__in=[207, 218,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([15])
        mod.save()

    #POSGRADO
    qsmodulos = Modulo.objects.filter(id__in=[318,
                                                277,
                                                319,
                                                320,
                                                ])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([7])
        mod.save()

    #SERVICIOS
    qsmodulos = Modulo.objects.filter(id__in=[486,
                                                388,
                                                484,
                                                313,
                                                508,
                                                485,
                                                265,
                                                153,
                                                26,
                                                331,
                                                457,
                                                268,
                                                213,])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([6])
        mod.save()

    #RECURSOS Y HERRAMIENTAS
    qsmodulos = Modulo.objects.filter(id__in=[463,
                                                83,
                                                444,
                                                185,
                                                84,
                                                385,
                                                464,
                                                154,
                                                36,
                                                439,
                                                ])
    for mod in qsmodulos:
        print(mod)
        mod.categorias.set([5])
        mod.save()

modulossga()
#
# # def asignaturamalla_transversal():
# #     try:
# #         listmaterias = [60342,60354,59990,60165,59078,59079,56917,
# #                         56919,
# #                         56925,
# #                         57750,
# #                         57859,
# #                         57115,
# #                         57117,
# #                         57122,
# #                         57134,
# #                         57142,
# #                         57144,
# #                         57506,
# #                         56474,
# #                         56487,
# #                         57216,
# #                         57250,
# #                         57387,
# #                         57511,
# #                         57687,
# #                         57513,
# #                         57587,
# #                         60331,
# #                         60333,
# #                         58318,
# #                         58294,
# #                         58913,
# #                         60296,
# #                         60301,
# #                         60306,
# #                         60311,
# #                         58831,
# #                         58832,
# #                         58838,
# #                         58840,
# #                         60563,
# #                         60605,
# #                         60764,
# #                         60743,
# #                         52597,
# #                         52782,
# #                         60105,
# #                         56206,
# #                         56161,
# #                         56464,
# #                         56522,
# #                         56601,
# #                         59687,
# #                         56535,
# #                         52656,
# #                         60809,
# #                         60812,
# #                         58066,
# #                         58170,
# #                         58366,
# #                         60535,
# #                         60536,
# #                         59772,
# #                         60531,
# #                         60533,
# #                         58879,
# #                         58538,
# #                         58630,
# #                         58692,
# #                         58613,
# #                         58808,
# #                         58606,
# #                         57452,
# #                         57551,
# #                         57689,
# #                         57481,
# #                         57470,
# #                         60268,
# #                         59797,
# #                         56823,
# #                         56712,
# #                         60824,
# #                         56783,
# #                         57489,
# #                         56866,
# #                         57588,
# #                         57226,
# #                         59134,
# #                         59140,
# #                         59044,
# #                         59049,
# #                         59054,
# #                         60368,
# #                         60433,
# #                         60451,
# #                         60463,
# #                         60475,
# #                         60487,
# #                         60499,
# #                         60505,
# #                         60505,
# #                         58023,
# #                         59840,
# #                         57850,
# #                         59850,
# #                         59789,
# #                         60143,
# #                         59790,
# #                         60183,
# #                         56687,
# #                         60371,
# #                         57107,
# #                         57114,
# #                         60322,
# #                         59857,
# #                         60319,
# #                         56441,
# #                         56497,
# #                         59862,
# #                         59867,
# #                         60849,
# #                         60852,
# #                         60853,
# #                         60855,
# #                         60856,
# #                         60928,
# #                         60929,
# #                         58172,
# #                         58080,
# #                         58299,
# #                         58319,
# #                         58562,
# #                         58834,
# #                         58835,
# #                         58837,
# #                         58828,
# #                         58713,
# #                         58775,
# #                         58962,
# #                         60298,
# #                         60303,
# #                         60308,
# #                         60313,
# #                         60537,
# #                         58675,
# #                         58680,
# #                         58652,
# #                         60770,
# #                         60749,
# #                         52577,
# #                         52790,
# #                         59802,
# #                         60253,
# #                         60130,
# #                         56120,
# #                         56213,
# #                         56414,
# #                         61095,
# #                         61100,
# #                         52664,
# #                         60810,
# #                         60813,
# #                         60544,
# #                         58090,
# #                         60534,
# #                         58465,
# #                         58404,
# #                         59770,
# #                         58051,
# #                         58300,
# #                         58752,
# #                         60517,
# #                         60519,
# #                         60521,
# #                         60522,
# #                         56947,
# #                         60124,
# #                         60946,
# #                         60282,
# #                         60286,
# #                         56296,
# #                         56316,
# #                         56274,
# #                         59817,
# #                         59823,
# #                         59829,
# #                         56735,
# #                         56808,
# #                         56720,
# #                         56732,
# #                         56907,
# #                         57608,
# #                         57622,
# #                         57638,
# #                         57647,
# #                         57518,
# #                         57639,
# #                         58025,
# #                         60391,
# #                         60438,
# #                         60455,
# #                         60467,
# #                         60467,
# #                         57806,
# #                         57920,
# #                         56595,
# #                         60370,
# #                         60372,
# #                         57002,
# #                         57808,
# #                         57902,
# #                         57463,
# #                         57508,
# #                         57509,
# #                         56968,
# #                         57048,
# #                         57510,
# #                         56944,
# #                         59983,
# #                         58289,
# #                         58282,
# #                         58694,
# #                         58684,
# #                         58626,
# #                         58739,
# #                         59526,
# #                         59531,
# #                         59536,
# #                         59541,
# #                         58401,
# #                         58409,
# #                         58439,
# #                         58640,
# #                         58821,
# #                         58824,
# #                         58825,
# #                         60571,
# #                         60613,
# #                         60774,
# #                         60753,
# #                         52559,
# #                         52777,
# #                         56430,
# #                         52638,
# #                         60878,
# #                         59917,
# #                         58146,
# #                         60932,
# #                         57600,
# #                         56268,
# #                         56269,
# #                         59256,
# #                         56706,
# #                         56704,
# #                         59193,
# #                         59198,
# #                         59204,
# #                         59209,
# #                         59213,
# #                         59224,
# #                         57352,
# #                         57427,
# #                         57582,
# #                         57399, ]
# #         materias = Materia.objects.filter(id__in=listmaterias).distinct()
# #         lista=[]
# #         print('Inicio recorrido '+ str(len(materias)))
# #         for materia in materias:
# #             asignaturamalla=materia.asignaturamalla
# #             if asignaturamalla:
# #                 asignaturamalla.transversal=True
# #                 asignaturamalla.save()
# #                 if asignaturamalla.id not in lista:
# #                     lista.append(asignaturamalla.id)
# #             else:
# #                 print('No hay asignatura')
# #         print(len(lista))
# #         print(str(lista))
# #         print('Finalizo con exito')
# #     except Exception as ex:
# #         print(str(ex))

# def inscripcion_erroneas():
#     try:
#         # (
#         # 38784, 38802, 38810,38817, 38828, 38829, 38831, 38833, 38834, 38835, 38841,
#         # 38845, 38849, 38856,39200, 38863, 38861, 38859, 38855, 38857, 33694, 33759,
#         # 33761, 33770, 33776,38004, 38704, 38713, 38737, 28230, 24711, 27127, 28153,
#         # 28226, 29129, 29167,30078, 30183, 30450, 30454, 32217, 32219, 22559, 22640,
#         # 18274, 17545, 23054,23257, 1928,  44166, 44175, 44177, 44190, 44199, 44200,
#         # 44201, 44205, 44207,44209, 44220, 44224, 44228, 44235, 44241, 44243, 44246,
#         # 44252, 44253, 44255,44256, 44258, 44260, 44261, 44266, 44267, 44273, 44274,
#         # 44275, 44276, 44282,44300, 44305, 44308, 44320, 44328, 45308, 44107, 44135,
#         # 44137, 44155, 44156,44165)
#         cedulas = ['0928809995',
#                           '0929600336',
#                           '0954698718',
#                           '0942242868',
#                           '0919618991',
#                           '0940329378',
#                           '0952559987',
#                           '0940328743',
#                           '0940125610',
#                           '0959026279',
#                           '0955553623',
#                           '0941150989',
#                           '0923796502',
#                           '0942119272',
#                           '0941140519',
#                           '0942533571',
#                           '0953947074',
#                           '0923179337',
#                           '0958795411',
#                           '0957552417',
#                           '1207008689',
#                           '0925856957',
#                           '0929027787',
#                           '0942124272',
#                           '0952909729',
#                           '0942448606',
#                           '0958791428',
#                           '0942098435',
#                           '0928171826',
#                           '0941344996',
#                           '0941794083',
#                           '0952535458',
#                           '2450108366',
#                           '0920895927',
#                           '0929134815',
#                           '0921512109',
#                           '0932306756',
#                           '0953614492',
#                           '0954846317',
#                           '0943573147',
#                           '0925335390',
#                           '1206326017',
#                           '0954221016',
#                           '1206494310',
#                           '0957552847',
#                           '0950475517',
#                           '0921281614',
#                           '0920697588',
#                           '0929858363',
#                           '0951996818',
#                           '0942059486',
#                           '0952268720',
#                           '0956266167',
#                           '0942098211',
#                           '0916368459',
#                           '0940151285',
#                           '0302558382',
#                           '0929211225',
#                           '0955508536',
#                           '0956876320',
#                           '0942487463',
#                           '0919872200',
#                           '0953700622',
#                           '0942345364',
#                           '0954164836',
#                           '0927994319',
#                           '1317708301',
#                           '0942077587',
#                           '0958403123',
#                           '0940354814',
#                           '0928806124',
#                           '0941343071',
#                           '0928933159',
#                           '1104596976',
#                           '0503245151',
#                           '1207234624',
#                           '0941566648',
#                           '1400777601',
#                           '0942484635',
#                           '0925409732',
#                           '0942384504',
#                           '0943290205',
#                           '0954051694',
#                           '0921653010',
#                           '0928738731',
#                           '1250329727',
#                           '0955152434',
#                           '0941995268',
#                           '0942483751',
#                           '0804141406',
#                           '0928952209',
#                           '0951657063',
#                           '0803795046',
#                           '0927424168',
#                           '0302553532', ]
#         listainscritos=[
#                         ('11513','0928809995'),
#                         ('11513','0929600336'),
#                         ('06016','0954698718'),
#                         ('11513','0942242868'),
#                         ('11513','0919618991'),
#                         ('11513','0940329378'),
#                         ('11513','0952559987'),
#                         ('11513','0940328743'),
#                         ('11513','0940125610'),
#                         ('11513','0959026279'),
#                         ('11513','0955553623'),
#                         ('11513','0941150989'),
#                         ('11513','0923796502'),
#                         ('11513','0942119272'),
#                         ('11513','0941140519'),
#                         ('06016','0942533571'),
#                         ('06016','0953947074'),
#                         ('06016','0923179337'),
#                          ('11513','0958795411'),
#                          ('11513','0957552417'),
#                          ('11513','1207008689'),
#                          ('11513','0925856957'),
#                          ('11513','0929027787'),
#                          ('06016','0942124272'),
#                          ('06016','0952909729'),
#                          ('06016','0942448606'),
#                          ('06016','0958791428'),
#                          ('06016','0942098435'),
#                          ('06016','0928171826'),
#                          ('06016','0941344996'),
#                          ('06016','0941794083'),
#                          ('11513','0952535458'),
#                          ('11513','2450108366'),
#                          ('06016','0920895927'),
#                          ('06016','0929134815'),
#                          ('06016','0921512109'),
#                          ('11513','0932306756'),
#                          ('06016','0953614492'),
#                          ('06016','0954846317'),
#                          ('06016','0943573147'),
#                          ('06016','0925335390'),
#                          ('06016','1206326017'),
#                          ('06016','0954221016'),
#                          ('06016','1206494310'),
#                          ('06016','0957552847'),
#                          ('06016','0950475517'),
#                          ('06016','0921281614'),
#                          ('06016','0920697588'),
#                          ('11513','0929858363'),
#                          ('11513','0951996818'),
#                          ('11513','0942059486'),
#                          ('06016','0952268720'),
#                          ('06016','0956266167'),
#                          ('11513','0942098211'),
#                          ('11513','0916368459'),
#                          ('06016','0940151285'),
#                          ('11513','0302558382'),
#                          ('11513','0929211225'),
#                          ('11513','0955508536'),
#                          ('11513','0956876320'),
#                          ('11513','0942487463'),
#                          ('11513','0919872200'),
#                          ('11513','0953700622'),
#                          ('11513','0942345364'),
#                          ('11513','0954164836'),
#                          ('11513','0927994319'),
#                          ('11513','1317708301'),
#                          ('11513','0942077587'),
#                          ('06016','0958403123'),
#                          ('11513','0940354814'),
#                          ('11513','0928806124'),
#                          ('11513','0941343071'),
#                          ('11513','0928933159'),
#                          ('11513','1104596976'),
#                          ('06016','0503245151'),
#                          ('06016','1207234624'),
#                          ('11513','0941566648'),
#                          ('11513','1400777601'),
#                          ('11513','0942484635'),
#                          ('11513','0925409732'),
#                          ('06016','0942384504'),
#                          ('11513','0943290205'),
#                          ('11513','0954051694'),
#                          ('11513','0921653010'),
#                          ('06016','0928738731'),
#                          ('11513','1250329727'),
#                          ('11513','0955152434'),
#                          ('11513','0941995268'),
#                          ('11513','0942483751'),
#                          ('11513','0804141406'),
#                          ('11513','0928952209'),
#                          ('06016','0951657063'),
#                          ('06016','0803795046'),
#                          ('11513','0927424168'),
#                          ('11513','0302553532'),
#                         ]
#         inscritos = Inscripcion.objects.filter(persona__cedula__in=cedulas).distinct()
#         lista=[]
#         print('Inicio recorrido '+ str(len(inscritos)))
#         for inscrito in inscritos:
#             for ins in listainscritos:
#                 if ins[1] == inscrito.persona.cedula and ins[0] == inscrito.carrera.codigo:
#                     nivelmalla=inscrito.mi_nivel().nivel
#                     lista.append(inscrito.id)
#         print(len(lista))
#         print(str(lista))
#         matricula=Matricula.objects.filter(id__in=lista).values_list('id')
#         mids=list(matricula)
#         print(f'Total de matriculas {len(matricula)}')
#         print(str(mids))
#         print('Finalizo con exito')
#     except Exception as ex:
#         print(str(ex))

# inscripcion_erroneas()


# def eliminar_constataciones():
#     constataciones=DetalleConstatacionFisicaActivoTecnologico.objects.filter(Q(status=True )& Q(activo__activotecnologico__statusactivo=2) | Q(activo__activotecnologico__procesobaja=True))
#     informes=InformeActivoBaja.objects.filter(status=True)
#     lista=[]
#     for informe in informes:
#         lista.append(informe.activofijo.id)
#     print(lista)
#     for constatacion in constataciones:
#         constatacion.status=False
#         constatacion.save()
#
# eliminar_constataciones()

# Pruebas de firma de documento para captar errores
def firmar_documento_sri():
    import subprocess
    from django.db import transaction
    import os
    from sga.funciones import notificacion as notify
    from sga.models import Persona
    from settings import FORMA_PAGO_EFECTIVO, FORMA_PAGO_TARJETA, FORMA_PAGO_CHEQUE, FORMA_PAGO_DEPOSITO, \
        FORMA_PAGO_TRANSFERENCIA, \
        DESCUENTOS_EN_FACTURAS, FORMA_PAGO_ELECTRONICO, FORMA_PAGO_CUENTA_PORCOBRAR, TIPO_AMBIENTE_FACTURACION, \
        JR_JAVA_COMMAND, JR_RUN_SING_SIGNCLI, PASSSWORD_SIGNCLI, SERVER_URL_SIGNCLI, SERVER_USER_SIGNCLI, \
        SERVER_PASS_SIGNCLI, SITE_STORAGE, REPORTE_PDF_FACTURA_ID, JR_RUN, DATABASES, URL_SERVICIO_ENVIO_SRI_PRUEBAS, \
        URL_SERVICIO_ENVIO_SRI_PRODUCCION, URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS, URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION, \
        DEBUG, SUBREPOTRS_FOLDER, RUBRO_ARANCEL, RUBRO_MATRICULA
    from sagest.models import Factura
    adm1 = Persona.objects.get(id=27762)
    adm2 = Persona.objects.get(id=36111)
    mensaje_notificacion = f'Proceso de facturación: '
    try:
        facturas = Factura.objects.filter(Q(autorizada=False) | Q(enviadacliente=False), valida=True, xmlgenerado=True, firmada=False, enviadasri=False, autorizada=False, enviadacliente=False).distinct()
        count = facturas.count()
        adm1 = Persona.objects.get(id=27762)
        adm2 = Persona.objects.get(id=36111)
        mensaje = f'# Facturas: {count}'
        titulo = 'Proceso de facturación'

        notify(titulo, mensaje, adm1, None, '/notificacion', adm1.pk, 1, 'sga-sagest', Factura, None)
        notify(titulo, mensaje, adm2, None, '/notificacion', adm2.pk, 1, 'sga-sagest',Factura,None)
        for factura in facturas[:3]:
            token = miinstitucion().token
            if not token:
                notify('No hay token', '', adm2, None,
                       f'', adm2.id, 2, 'sga-sagest',
                       Persona, None)

            runjrcommand = [JR_JAVA_COMMAND, '-jar',
                            os.path.join(JR_RUN_SING_SIGNCLI, 'SignCLI.jar'),
                            token.file.name,
                            PASSSWORD_SIGNCLI,
                            SERVER_URL_SIGNCLI + "/sign_factura/" + factura.weburl]
            if SERVER_USER_SIGNCLI and SERVER_PASS_SIGNCLI:
                runjrcommand.append(SERVER_USER_SIGNCLI)
                runjrcommand.append(SERVER_PASS_SIGNCLI)
            runjr = subprocess.call(runjrcommand)
            mensaje_notificacion+=' | ' + str(runjr)
        notify('Finalizado con éxito', f'{mensaje_notificacion}', adm2, None,
               f'', adm2.id, 2, 'sga-sagest',
               Persona, None)
    except Exception as ex:
        # transaction.set_rollback(True)
        mensaje = 'Error ({}) al firmar en la linea: {}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
        notify('Error en firmar', mensaje, adm2, None,
               f'', adm2.id, 2, 'sga-sagest',
               Persona, None)

# firmar_documento_sri()