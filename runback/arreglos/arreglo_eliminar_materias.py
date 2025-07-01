import os
import sys
import xlsxwriter
import xlwt
import openpyxl
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *

#asignatudas
#TRABAJO DE TITULACIÓN I [TTI]  -id-1932
#DISEÑO DE LA INVESTIGACIÓN  -id - 2463
#THESIS SEMINAR I: ACADEMIC WRITING --3714
#SEMINARIO DE TITULACION I --3649
#TRABAJO DE GRADO I --3395

#carrera
#DERECHO EN LÍNEA id 126
#EDUCACIÓN BÁSICA EN LÍNEA --135
#PSICOLOGÍA EN LÍNEA ---132
#PEDAGOGÍA DE LOS IDIOMAS NACIONALES Y EXTRANJEROS EN LÍNEA --129
#TRABAJO SOCIAL EN LÍNEA -130
#ECONOMÍA EN LÍNEA --128
cedulasDatosEnlineaOctavo = ["0604067470", "0930184320", "0940326838", "1003156948", "1003156948", "0958178535",
                             "0958178535", "1203404643", "0909378465", "0942799198", "0930835137", "0704932615",
                             "0952024115", "1103352199", "1103352199", "1103352199", "1722063243", "0958323784",
                             "0958323784", "0921173142", "0931090831", "0931090831", "0958687675", "0955019138",
                             "0927160994", "0921409496", "0955399514", "0926376211", "0942376963", "0922057088", "0104550405", "0930328695", "0955467691", "1900526326", "0955751193", "1203592827", "0914891510", "1756471411", "1207201995", "1311567851", "1311567851", "0915038186", "0750118614", "1715077002", "0704365618", "0922987508", "1313456103", "1313456103", "1313456103", "1205688581", "0924431067", "1204779647", "1204779647", "0944136563", "0944136563", "0942757758", "2400010175", "0921984449", "0941349920", "0927739706", "0927739706", "0927739706", "1751284686", "1312618257", "0954875225", "0925106148", "0927996868", "0956401574", "0956401574", "0943571570", "0943571570", "1205538109", "1003295514", "0923168017", "0923168017", "0941334740", "1723299879", "0923073829", "0107263360",
                             "0107263360", "0924716764", "0706310943", "0706310943", "0706310943", "0706695681", "0956918502", "0956918502", "0924777436", "0924777436", "0704489798", "0704489798", "0926559121", "0927705053", "0942251877", "0202040481", "0944263466", "0944263466", "0944263466", "0953598646", "0703113886", "2300121965", "2300121965", "2300121965", "0922269543", "0955024864", "0955024864", "1754306791", "0923568950", "0923568950", "0942338757", "1804636338", "1804636338", "0952354892", "0952354892", "0952354892", "1204324345", "0927843045", "0603224411", "0925800633", "0926927328", "0707078630", "0924834245", "1105124430", "0927670380", "1105449696", "0803670025", "0803670025", "0703583120","1721760765", "0951902022", "0914214416", "0923795942", "0923795942", "0923795942", "0952881985", "0952881985", "0952881985", "0959053943", "0930179882", "1207479260", "1207479260", "1207479260", "0928369461", "0604244947", "1103999676", "0401688536", "0920463312", "0706233269", "1207775402", "1207775402", "0705952554", "0705952554", "0926423849", "0953162625", "1712432903", "1004631303", "0923894752", "0958393332", "0958393332", "0917786394", "0941643108", "0401246863", "1104664097", "1104664097", "1104664097", "0930898622", "1206786350", "1206786350", "1206322016", "0917501561", "2300135833", "2300135833", "0941881070", "1723310056", "1724754070", "1724754070", "1724754070", "0928105592", "1720450269", "1720450269", "0504030057", "0504030057", "0504030057", "1103379671", "0928797265", "0918865288", "0918865288", "0918865288", "0940568512", "0940568512", "0944056480", "0940123284", "0941377368", "0924602865", "0502708910", "0502708910", "0502708910", "0705096469", "0705096469", "0941333445", "0951285162", "0302655642", "0940974975", "0924075369", "0928819713", "0926717760", "0930458484", "0926176132", "0928172352", "0942500877", "0504111170", "1756158752", "0703729186", "0928987783", "0750193211", "0750193211", "0750193211", "1711948685", "0919820043", "0919820043", "0919820043", "2350201360", "1500496565", "0957077225", "0957077225", "0706990140", "0706990140", "1104969736", "1208390946", "1208390946", "1208390946", "0202231155", "1204803918", "0952883676", "0952883676", "0952883676", "1150594180", "0955367834", "0922863998", "1752296853", "1752296853", "0704409648", "0705364198", "0102803079", "0706040268", "0706708740", "1717606261", "0920235074", "0924727704", "0924727704", "0751037169", "1309402004", "1309402004", "1208295814", "0957488901", "0928765197"]


cedulasDatosEnlineaNoveno= ["0920930211", "0942265208", "1753782273", "0925749707", "0958763146", "0958763146", "0926162629", "2300795826", "0931940795", "0925521122", "0953278959", "0952496347", "0950564682", "0919871798", "1206613307", "0924516180", "0201870888", "0706356334", "0603128877", "0921282984", "0924396823", "0929489920", "0956549943", "0919412577", "0705804227", "0929580207", "0916958192", "0503793960", "2100829064", "0705437663", "0924589948", "0956669709", "0924609654", "0943821918", "0951961747", "0932042617", "1715831788", "0929351260", "0954284170", "0707172664", "0914109954", "0850572801", "0951306356", "0928106087", "1724349574", "1723393722", "1715384275", "0604143537", "1716341225", "0930155098", "0929896785", "0929011666", "0953367422", "0604039305", "0927427815", "1207604438", "1105421513", "0958425985", "0954199964", "0919232603", "0919425892", "1204931230", "1208926368", "1103915482", "0926146788", "0929347292", "1104494099", "0950490870", "0930485834", "1203036031", "1706073366", "0921808457", "1208013118", "0926133547", "1724137177", "0917885469", "1724462237", "2400298556", "1725122236", "0954782082", "0955342472", "0924810021", "0202367637", "1720882164", "1104612997", "0922318894", "0922318894", "0705561405", "0953514080", "0940453780", "0802744250", "0924521255", "0958275141", "0928600212", "0928600212", "1720831369", "0944148576", "0923555767", "0930101480", "0706557626",
                            "2450441817", "0705004943", "0922574520", "1716038961", "1716038961", "0957757578", "0958908824", "0958908824", "0958908824", "0923573679", "0929062305", "0940236409", "0915207823", "1726600297", "0930178496", "0959440298", "0923701544", "1104109887", "1717709925", "0804152999", "1717219289", "1104567217", "0920191103", "0914828306", "0926681578", "0954771416", "0953408796", "0953408796", "0921072443", "0930609417", "1204044968", "1204837031", "1314564269", "1104711690", "0921664926", "0750057333", "0706323359", "FB392233", "1803496239", "0940293194", "0928269695", "0928269695", "0802802454", "0953204781", "0923711170", "2100771233", "0605048453", "0919970426", "0932045313", "1003992052", "1728185016", "0604201350", "1206387936", "0952555910", "0916474406", "0926124470", "1206236901", "1206324590", "0606168813", "0952050680", "1707498372", "1001930229", "1001930229", "1400522700", "0921410924", "1204833923", "1207982511", "0705873438", "0202031746", "0912747888", "0704204007", "0911363166", "0604668038", "0202195913", "0952789790", "0952789790", "0921194874", "0918663428", "0923399513", "1724647118", "0926426529", "0917279291", "0922837158", "0930910302", "1713072385", "1752764801", "0958750242", "0923582746", "0942086554", "0942086554", "0930777883", "0930777883", "1002182812", "2100603352", "0503097883", "1104729783", "1250118583", "0911063394", "0303162655", "0703984039",
                            "0603928441", "0955390885", "0919647156", "1313024844", "0956022792", "1307884112", "0924084023", "0926693912", "0955798087", "0924121270", "1004163323", "0941342693", "0105868699", "1712621505", "1722797071", "1716989031", "0941536674", "1709890188", "1751340371", "0503108193", "0925648693", "0705049013", "0104261532", "0104261532", "0928288018", "0704459544", "0929766541", "0929766541", "0953406600", "0805418100", "0940749187", "0926487257", "1316824844", "0959170671", "0930411384", "1312163239", "0942113697", "1850123207", "0705189975", "0923122287", "1250181938", "0803012384", "0850203175", "0850203175", "0850203175", "0928047992", "0941142481", "0941142481", "0924734841", "0929487031", "0919619775", "0942439563", "0704320217", "0942071218", "1709267189"]

cedulasDatosPresencial= ["0942254228", "0941528481", "0942029190", "0952300168", "0931645444", "0943120964", "0958853822", "0927999599","0302667548", "1450174576", "0941990483","0950899443", "0955872783", "0955701008","0961256005", "0941320806", "0955595145", "0955595145", "0955791652", "0927953547", "0959034745", "0959034745", "0940496565", "0957229438", "0942194739", "0957420680", "0957420680", "0957420680", "0928551209", "0941526741", "0941114415", "0941114415", "0940350432", "0940350432", "0940350432", "0940350432", "0943692723", "0943692723", "0929315992", "0940111719", "0940111719", "0924604739", "0919413146", "0919413146", "0302868328", "0927576975", "0940782428", "0958635625", "0958026692", "0958026692", "0958026692", "0955920053", "0955920053", "0924309016", "0958577710", "0940153513", "0705113736", "0942071663", "0942071663", "0942071663", "0952161388",
                         "0941600215", "0954344149", "0953353216", "0958538977", "0958538977", "1205831207", "0929225993", "0953084530", "1206554014", "1206554014", "0927434233", "0929578706", "0950937060", "0923000475", "0941659021", "0930728266", "0930728266", "0928598093", "0952522415", "2450090291", "2450090291", "0942095019", "0942356064", "0942356064", "0942356064", "0957292634", "0706468378", "0941605495", "0941605495", "0302786397", "0928055326", "0929425528", "0929425528", "0923666184", "0954733325", "0943003913", "0925284002", "0958601536", "0942248451", "0940609324", "0940609324", "0940609324", "0940609324", "0930909791", "0951906064", "0940665524", "0941984106", "0941984106", "0953947686", "0956265144", "0954762175", "0957793912", "0957793912", "0955480041", "0926332263", "0940144454", "0955803952", "0302463088",
                         "0954158093", "0952559490", "0957978786", "0942193665", "0953960010", "0704692847", "0704692847", "0940323470", "0954888160", "1726499922", "0942490236", "0942490236", "1205915208", "0941601916", "0941601916", "0915686182", "0915686182", "0850795618", "0954948055", "0942058736", "0928981513", "0921525143", "0302271432", "0302271432", "0922981345", "0961521077", "1205283151", "0928792498", "0953745700", "0953745700", "0941336489", "0953852308", "0953852308", "0953156049", "0953156049", "0942242207", "0923656334", "0959092925", "0959092925", "0930963418", "0941120826", "0940996630", "0940935547", "0940935547", "0940390586", "1317948485", "0941325789", "0941325789", "0952464048", "0940905029", "1206706747", "0923811434", "0929134286", "0929134286", "0955787924", "0942055484", "0940810070", "0958967465", "0931770242", "0931483648", "0931483648", "0952659290", "0952166742", "0952166742",
                         "0942439860", "0941529042", "0953062353", "0953062353", "0923208094", "0921177788", "0605048149", "0952546299", "1207839893", "0940114697", "0929856367", "0944385905", "0942121047", "0942121047", "0942121047", "0959308156", "0950946921", "0950946921", "0956963177", "0927385351", "0956138960", "0955495163", "0941157729", "0941157729", "0931718332", "0942365966", "0942365966", "0924013741", "0924013741", "0926151226", "0926151226", "0926151226", "0928950278", "0953486446", "0953486446", "0928790724", "0957635709", "0944272046", "0940104813", "0943598011", "0940582471", "0940582471", "0943190074", "0943190074", "0924019045", "0942491705", "0942491705", "0927959742", "0955784210", "0923220909", "0923220909", "0923220909", "0955129226", "0928067040", "0955956917", "0955956917", "0943780890", "0952560571", "0952560571", "0929566883", "0923170229", "0923170229", "0923170229", "0929076149", "0929076149", "0952117497", "0952117497", "0942097189", "0942097189",
                         "0750133571", "0929362499", "0941881781", "0931312086", "0951194315", "0951194315", "1729750842", "1751219278", "0952118446", "0952118446", "0952118446", "0955508148", "0942531534", "0915864961", "0952359230", "0952359230", "0951688183", "0955614599", "0923937288", "0930159884", "0930468707", "0954970083", "0941798639", "0926302365", "0926302365", "0926302365", "0923375562", "0940142532", "0940142532", "0929158202", "0919612150", "0940906266", "0940935174", "0940935174", "0951896588", "0951896588", "0942095373", "0942095373", "0942095373", "0952061281", "0955416599", "0929973519", "0942233495", "0941601445", "0941601445", "1207506914", "1207506914", "0954331880", "0952780955", "0606230886", "1207344233", "0957886526", "0957886526", "0957886526", "2101003040", "2101003040", "2101003040", "2101003040", "0952487239", "0954640512", "0954640512", "0928261536", "0954144325", "0954144325", "0955509179", "0955509179", "0942098039", "0942126590",
                         "0605190982", "0943382531", "0942193897", "0942193897", "0918502535", "0954327268", "0955189758", "0953506318", "0923647614", "0929593366", "0930724711", "0931713929", "0931713929", "0951948223", "0951804467", "0951804467", "0952059459", "0959423732", "0955391040", "0955391040", "0955391040", "0921655601", "0930551254", "0930551254", "0929266427", "0929266427", "0928477793", "0922980966", "0922980966", "0951971043", "0924308299", "0920779121", "0920779121", "0955267042", "0952386944", "0955369467", "0950926550", "0955891304", "0929249324", "0943639732", "0926403049", "0926402652", "0944169853", "0944169853", "0605006444", "0605006444", "0107054603", "0953826500", "0953826500", "0928858224", "0928858224", "0957090228", "0957090228", "0953937216", "0955627021", "0953194636", "0926858739", "0925458358", "0958195752", "1724929292", "0927311712", "0927311712"]


def desmatricular(periodo,carrera,id_Asignatura,cedulasDatos, inscripcion):
    #carreraDerecho=126
    #cedula='0604067470'
    cont=1
    for cedula in cedulasDatos:

        for materiaasignada in MateriaAsignada.objects.filter(status=True, materia__status=True,
                                                  materia__nivel__status=True,
                                                  materia__asignatura_id=id_Asignatura, materia__nivel__periodo_id=periodo,
                                                  matricula__inscripcion__persona__cedula=cedula,
                                                  matricula__inscripcion__carrera_id=carrera,
                                                  matricula__inscripcion_id=inscripcion):
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            print(matricula.inscripcion, matricula.inscripcion.carrera, materiaasignada.materia)
            materia.cupo -= 1
            materia.totalmatriculadocupoadicional -= 1
            materia.save()
            materiaasignada.delete()
            matricula.actualizar_horas_creditos()
        cont = cont + 1
    print(cont)

def desmatricular_2(matricula, materia):
    #carreraDerecho=126
    #cedula='0604067470'
    cont=1


    for materiaasignada in MateriaAsignada.objects.filter(status=True, materia__status=True,
                                                              materia__nivel__status=True,
                                                              materia=materia,
                                                              matricula=matricula):
        materia = materiaasignada.materia
        matricula = materiaasignada.matricula
        # print(matricula.inscripcion, matricula.inscripcion.carrera, materiaasignada.materia)
        materia.cupo -= 1
        materia.totalmatriculadocupoadicional -= 1
        materia.save()
        materiaasignada.delete()
        matricula.actualizar_horas_creditos()
        cont = cont + 1
    # print(cont)


def matricular(periodo,carrera,id_Asignatura,cedulasDatos):
    try:
        cont=1
        for cedula in cedulasDatos:
            if cedula:
                matricula = Matricula.objects.filter(status=True, inscripcion__persona__cedula=cedula, nivel__periodo_id=periodo).first()
                materia = Materia.objects.filter(status=True, nivel__status=True, asignatura_id=id_Asignatura,
                                                 nivel__periodo_id=periodo, asignaturamalla__malla__carrera_id=carrera).first()
                for m in materias:
                    materia2 = Materia.objects.filter(status=True, nivel__status=True, asignatura_id=int(m[1]),
                                                     nivel__periodo_id=periodo,
                                                     asignaturamalla__malla__carrera_id=int(m[0])).first()
                    if not int(m[0]) == matricula.inscripcion.carrera_id and \
                            MateriaAsignada.objects.filter(status=True, materia__status=True, matricula=matricula,
                                                           materia=materia2,
                                                           materia__nivel__periodo_id=periodo).exists():
                        desmatricular_2(matricula, materia2)
                malla = matricula.inscripcion.mi_malla()
                # requisitostitulacion = malla.requisitotitulacionmalla_set.filter(status=True)
                asig = malla.asignaturamalla_set.filter(asignatura_id=id_Asignatura).first()
                if asig:
                    requisitostitulacion = asig.requisitoingresounidadintegracioncurricular_set.filter(status=True, activo=True)
                    if verificar_titulacion(requisitostitulacion, matricula.inscripcion_id):
                        if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia).exists():
                            if matricula.inscripcion.carrera_id == carrera:
                                print(matricula.inscripcion, matricula.inscripcion.carrera, materia)
                                if matricula.inscripcion.carrera.modalidad == 3:
                                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                                      materia=materia,
                                                                      notafinal=0,
                                                                      sinasistencia=True,
                                                                      asistenciafinal=100,
                                                                      cerrado=False,
                                                                      observaciones='',
                                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                                else:
                                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                                      materia=materia,
                                                                      notafinal=0,
                                                                      asistenciafinal=0,
                                                                      cerrado=False,
                                                                      observaciones='',
                                                                      estado_id=NOTA_ESTADO_EN_CURSO)

                                materiaasignada.save()
                                materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                                materiaasignada.asistencias()
                                materiaasignada.evaluacion()
                                materiaasignada.mis_planificaciones()
                                materiaasignada.save()
                                materia.cupo += 1
                                materia.totalmatriculadocupoadicional += 1
                                materia.save()
                                matricula.actualizar_horas_creditos()
                                cont = cont + 1
                                print('MATRICULADO')
                        else:
                            print(matricula.inscripcion)
                            print('ESTUDIANTE ESTA MATRICULADO')
                    else:
                        print(matricula.inscripcion)
                        if MateriaAsignada.objects.filter(matricula=matricula, materia=materia).exists():
                            desmatricular_2(matricula, materia)
                        print('')
                        print('ESTUDIANTE NO CUMPLE')
                        print('')
    except Exception as ex:
        print(ex)


def verificar_titulacion(requisitostitulacion, inscripcion_id):
    try:
        for requisito in requisitostitulacion:
            valor = requisito.run(inscripcion_id)
            if not valor:
                return False
        return True
    except Exception as ex:
        return False


materias = [[126,2463],[135,1932],[132,1932],
            [129,3714],[130,3649],[128,3395],

            [126, 3701], [135, 1933], [132, 1933], [129, 3734],
            [130, 3660], [128, 3396], [127, 1932], [131, 1933], [134, 1870],

            [160,3978], [137,4355], [140,3978], [151,3978],
            [146,4355], [139,4271], [141,3978], [149,4447],
            [153,4271], [158,4355,], [143,4345],[156,4380],
            [142,3978], [157,4345]
            ]
#DESMATRICULACION EN LINEA OCTAVO

#eliminar materia DISEÑO DE LA INVESTIGACIÓN carrera de derecho
# DISEÑO DE LA INVESTIGACIÓN   DERECHO EN LÍNEA
matricular(177,126,2463,cedulasDatosEnlineaOctavo)
#eliminar materia TRABAJO DE TITULACIÓN I [TTI] carrera EDUCACIÓN BÁSICA EN LÍNEA
matricular(177,135,1932,cedulasDatosEnlineaOctavo)
#eliminar materia TRABAJO DE TITULACIÓN I [TTI] carrera PSICOLOGÍA EN LÍNEA
matricular(177,132,1932,cedulasDatosEnlineaOctavo)
#eliminar materia THESIS SEMINAR I: ACADEMIC WRITING  carrera PEDAGOGÍA DE LOS IDIOMAS NACIONALES Y EXTRANJEROS EN LÍNEA
matricular(177,129,3714,cedulasDatosEnlineaOctavo)
#eliminar materia SEMINARIO DE TITULACION I carrera TRABAJO SOCIAL EN LÍNEA
matricular(177,130,3649,cedulasDatosEnlineaOctavo)
#eliminar materia TRABAJO DE GRADO I carrera ECONOMÍA EN LÍNEA
matricular(177,128,3395,cedulasDatosEnlineaOctavo)



#DESMATRICULACION EN LINEA NOVENO
#DERECHO EN LÍNEA id-- 126 // DESARROLLO DE LA INVESTIGACIÓN Y PROCESO DE TITULACIÓN --3701
matricular(177,126,3701,cedulasDatosEnlineaNoveno)
#EDUCACIÓN BÁSICA EN LÍNEA --135 // TRABAJO DE TITULACIÓN II --1933
matricular(177,135,1933,cedulasDatosEnlineaNoveno)
#PSICOLOGÍA EN LÍNEA ---132  // TRABAJO DE TITULACIÓN II -- 1933
matricular(177,132,1933,cedulasDatosEnlineaNoveno)
#PEDAGOGÍA DE LOS IDIOMAS NACIONALES Y EXTRANJEROS EN LÍNEA --129 // 3734 -THESIS SEMINAR II: WORKSHOP FOR DESIGNING THE RESEARCH REPORT AND PREPARATION FOR THE COMPLEXIVE EXAM
matricular(177,129,3734,cedulasDatosEnlineaNoveno)
#TRABAJO SOCIAL EN LÍNEA -130  // SEMINARIO DE TITULACION II--3660
matricular(177,130,3660,cedulasDatosEnlineaNoveno)
#ECONOMÍA EN LÍNEA --128  // TRABAJO DE GRADO II --3396
matricular(177,128,3396,cedulasDatosEnlineaNoveno)
#EDUCACIÓN INICIAL EN LÍNEA --127 //TRABAJO DE TITULACIÓN I -- 1932
matricular(177,127,1932,cedulasDatosEnlineaNoveno)
#COMUNICACIÓN EN LÍNEA-131 // TRABAJO DE TITULACIÓN II -- 1933
matricular(177,131,1933,cedulasDatosEnlineaNoveno)
#TURISMO EN LÍNEA --134  //  TRABAJO DE TITULACIÓN -- 1870
matricular(177,134,1870,cedulasDatosEnlineaNoveno)


#DESMATRICULACION PRESENCIAL
#TRABAJO SOCIAL 2019 id 160  //	DISEÑO DE INTEGRACION CURRICULAR id 3978
matricular(177,160,3978,cedulasDatosPresencial)
#LICENCIATURA EN PSICOLOGIA 2019  id 137//	INTEGRACIÓN CURRICULAR id 4355
matricular(177,137,4355,cedulasDatosPresencial)
# ADMINISTRACION DE EMPRESAS 2019 id 140  //	DISEÑO DE INTEGRACION CURRICULAR id 3978
matricular(177,140,3978,cedulasDatosPresencial)
# INGENIERÍA AMBIENTAL 2019 id 151//	DISEÑO DE INTEGRACION CURRICULAR id 3978
matricular(177,151,3978,cedulasDatosPresencial)
# BIOTECNOLOGIA 2019 id 146 //	INTEGRACIÓN CURRICULAR id 4355
matricular(177,146,4355,cedulasDatosPresencial)
# SOFTWARE 2019 id 139 //	DISEÑO DE INTEGRACIÓN CURRICULAR id 4271-----ojo
matricular(177,139,4271,cedulasDatosPresencial)
# CONTABILIDAD Y AUDITORIA 2019 id 141 //	DISEÑO DE INTEGRACION CURRICULAR id 4271
matricular(177,141,3978,cedulasDatosPresencial)
# EDUCACIÓN INICIAL 2019 id 149  //	INTEGRACIÓN CURRICULAR EDUINI--- id 4447
matricular(177,149,4447,cedulasDatosPresencial)
# INGENIERIA INDUSTRIAL 2019 id 153  //	DISEÑO DE INTEGRACION CURRICULAR id 3978----ojo
matricular(177,153,4271,cedulasDatosPresencial)
# ECONOMIA 2019	id 158  //  INTEGRACIÓN CURRICULAR id 4355
matricular(177,158,4355,cedulasDatosPresencial)
# COMUNICACIÓN 2019	id 143  // UNIDAD DE INTEGRACIÓN CURRICULAR  id 4345
matricular(177,143,4345,cedulasDatosPresencial)
# EDUCACIÓN 2019 id 156  //	UNIDAD DE INTEGRACIÓN id 4380
matricular(177,156,4380,cedulasDatosPresencial)
# PEDAGOGÍA DE LA ACTIVIDAD FISICA Y DEPORTE 2019 id 142  //	DISEÑO DE INTEGRACION CURRICULAR id 3978
matricular(177,142,3978,cedulasDatosPresencial)
# PEDAGOGÍA DE LOS IDIOMAS NACIONALES Y EXTRANJEROS 2019 id 157  //	id 4345 UNIDAD DE INTEGRACIÓN CURRICULAR
matricular(177,157,4345,cedulasDatosPresencial)








