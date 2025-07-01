import json
import os
import sys
from decimal import Decimal

from django.db import connections
from django.db.models import Count

from settings import PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, RUBRO_ARANCEL, RUBRO_MATRICULA, PORCENTAJE_MULTA
from sga.models import AsignaturaMalla, Materia, Inscripcion, Periodo, ModuloMalla
from sga.templatetags.sga_extras import encrypt_alu

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
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")
application = get_wsgi_application()

from sga.models import Materia



def agregacion_aux(request):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))

        periodo = Periodo.objects.get(pk=request.POST['pid'])
        mismaterias = json.loads(request.POST['materias'])
        if inscripcion.coordinacion_id != 9 and inscripcion.coordinacion_id != 7:
            cantidad_seleccionadas = 0
            idsmaterias = []
            # cursor = connections['default'].cursor()
            # sql = "select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id=" + str(self.id) + " and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
            # cursor.execute(sql)
            # results = cursor.fetchall()
            nivel = 0
            # for per in results:

            for niv in mismaterias:
                idsmaterias.append(int(encrypt_alu(niv['idmat'])))
            asigmat = Materia.objects.filter(id__in=idsmaterias).values('asignaturamalla__nivelmalla_id').annotate(cantidadmateriasseleccionadas=Count('asignaturamalla__nivelmalla_id')).order_by('-cantidadmateriasseleccionadas').first()
            nivel = asigmat['asignaturamalla__nivelmalla_id']
            cantidad_seleccionadas = asigmat['cantidadmateriasseleccionadas']
            cantidad_nivel = 0
            for asignaturamalla in AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True, malla=inscripcion.mi_malla()):
                if Materia.objects.filter(nivel__periodo=periodo, asignaturamalla=asignaturamalla).exists():
                    if inscripcion.estado_asignatura(asignaturamalla.asignatura) != 1:
                        cantidad_nivel += 1

            porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD)) / 100).quantize(Decimal('.00')), 0))
            cobro = 0
            if inscripcion.estado_gratuidad == 1 or inscripcion.estado_gratuidad == 2:
                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                    cobro = 1
                else:
                    # if self.inscripcion.estado_gratuidad == 2:
                    cobro = 2
            else:
                if inscripcion.estado_gratuidad == 2:
                    cobro = 2
                else:
                    cobro = 3

            if inscripcion.persona.tiene_otro_titulo(inscripcion=inscripcion):
                cobro = 3

            from sagest.models import TipoOtroRubro, Rubro
            from django.db import transaction
            from django.http import JsonResponse
            persona = inscripcion.persona
            periodo = periodo
            totalmat = 0
            valor = 0
            if not inscripcion.persona.fichasocioeconomicainec_set.all().exists():
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "reload": False, "mensaje": u"No puede matricularse, debe llenar la ficha socioeconomica"})
            valorgrupoeconomico = inscripcion.persona.fichasocioeconomicainec_set.filter(status=True).first().grupoeconomico.periodogruposocioeconomico_set.filter(status=True, periodo=periodo).first().valor
            porcentaje_gratuidad = periodo.porcentaje_gratuidad
            valor_maximo = periodo.valor_maximo
            costo_materia_total = 0
            tiporubroarancel = TipoOtroRubro.objects.filter(pk=RUBRO_ARANCEL)[0]
            tiporubromatricula = TipoOtroRubro.objects.filter(pk=RUBRO_MATRICULA)[0]
            if cobro > 0:
                for materiaasignada in Materia.objects.filter(id__in=idsmaterias, status=True):
                    costo_materia = 0
                    creditos_para_cobro = materiaasignada.creditos
                    if existe_modulo_en_malla(inscripcion, materiaasignada):
                        creditos_para_cobro = materia_modulo_malla(inscripcion, materiaasignada).creditos
                    if cobro == 1:
                        costo_materia = Decimal(Decimal(creditos_para_cobro).quantize(
                            Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
                    else:
                        if cobro == 2:
                            cant = materiaasignada.cantidad_matriculas(inscripcion)
                            if cant is not None and cant > 1:
                                costo_materia = Decimal(Decimal(creditos_para_cobro).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
                        else:
                            costo_materia = Decimal(Decimal(creditos_para_cobro).quantize(Decimal('.01')) * valorgrupoeconomico).quantize(Decimal('.01'))
                    costo_materia_total += costo_materia

            if costo_materia_total > 0:
                valor_porcentaje = Decimal((costo_materia_total * porcentaje_gratuidad) / 100).quantize(Decimal('.01'))
                valor = valor_porcentaje
                if valor_porcentaje > valor_maximo:
                    valor = valor_maximo
            totalmat = costo_materia_total + valor
            return float(totalmat)


    except Exception as e:
        print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, e))
        print(e)



def existe_modulo_en_malla(inscripcion, materia):
        im = inscripcion.malla_inscripcion()
        if im:
            if im.malla.modulomalla_set.values("id").filter(asignatura=materia.asignatura).exists():
                return True
        return False



def materia_modulo_malla(inscripcion, materia):
        im = inscripcion.malla_inscripcion()
        if im:
            return ModuloMalla.objects.filter(asignatura=materia.asignatura, malla=im.malla)[0]
        return False
