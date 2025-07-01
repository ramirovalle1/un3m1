import os


from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, MatriculaSedeExamen

from django.db import transaction

from api.helpers.functions_helper import generate_qr_examen_final
from datetime import datetime


def generar_qr():
    materiasasignadas = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(status=True, aulaplanificacion__turnoplanificacion__fechaplanificacion__fecha='2024-01-06', materiaasignada__matricula__inscripcion__persona__cedula='0942076704')
    for materia in materiasasignadas:
        matricula = materia.materiaasignada.matricula
        matriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=matricula.id)
        print(u"matricula - %s" % matricula)
        with transaction.atomic():
            try:
                if matriculaSedeExamen.aceptotermino:
                    try:
                        result = generate_qr_examen_final(materia,
                                                          materiaasignada_id=materia.materiaasignada_id)
                        isSuccess = result.get('isSuccess', False)
                        if not isSuccess:
                            raise NameError('Error al generar documento')
                        aDataExamen = result.get('data', {})
                        url_pdf_examen = aDataExamen.get('url_pdf', '')
                        codigo_qr_examen = aDataExamen.get('codigo_qr', '')
                        if url_pdf_examen == '' and codigo_qr_examen == '':
                            raise NameError(u"No se encontro url del documento")
                        materia.fecha_qr = datetime.now()
                        materia.url_qr = f"/media/{url_pdf_examen}"
                        materia.codigo_qr = codigo_qr_examen
                        genero_qr = True
                        materia.save()
                    except Exception as ex:
                        materia.fecha_qr = None
                        materia.url_qr = None
                        materia.codigo_qr = None
                        genero_qr = False
                        materia.save()
            except Exception as ex:
                transaction.set_rollback(True)
                print(ex)

generar_qr()