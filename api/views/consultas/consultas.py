# coding=utf-8
import json
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.response_herlper import Helper_Response
from sga.models import PerfilUsuario, Persona

class EmailAPIView(APIView):

    def get(self, request, correo):
        try:
            if correo == '':
                raise NameError('Debe ingresar un correo valido')
            _eData = []
            if ePersona := Persona.objects.filter(emailinst__icontains=correo).first():
                _identificacion = ePersona.identificacion()
                _nombres = ePersona.nombres
                _apellidos = f'{ePersona.apellido1} {ePersona.apellido2}'
                perfilespersona = PerfilUsuario.objects.filter(status=True, persona=ePersona, visible=True)
                ePeriodo_id = 317

                for p in perfilespersona:
                    if p.es_estudiante():
                        if inscripcion := p.inscripcion:
                            if matricula := inscripcion.matricula_periodo(ePeriodo_id):
                                _eData.append({
                                    'identificacion': _identificacion,
                                    'nombres': _nombres,
                                    'apellidos': _apellidos,
                                    'perfil': p.__str__(),
                                    'carrera': inscripcion.carrera.__str__(),
                                    'facultad': inscripcion.coordinacion.__str__(),
                                    'nivel_matricula': str(matricula.nivelmalla) if matricula else 'No matriculado en el periodo vigente',
                                    'nivel_malla': str(inscripcion.mi_nivel().nivel),
                                    })

                    if p.es_profesor():
                        if docente := p.profesor:
                            distributivo = docente.profesordistributivohoras_set.filter(status=True, periodo_id=ePeriodo_id).first()
                            _eData.append({
                                'identificacion': _identificacion,
                                'nombres': _nombres,
                                'apellidos': _apellidos,
                                'perfil': p.__str__(),
                                'carrera': distributivo.carrera.__str__() if distributivo else 'Sin carrera en el periodo vigente',
                                'facultad': distributivo.coordinacion.__str__() if distributivo else 'Sin facultad en el periodo vigente',
                            })

                    if p.es_administrativo():
                        if administrativo := p.administrativo:
                            _eData.append({
                                'identificacion': _identificacion,
                                'nombres': _nombres,
                                'apellidos': _apellidos,
                                'perfil': p.__str__(),
                            })

            else:
                raise NameError('Persona no encontrada con el correo ingresado')
            return Helper_Response(isSuccess=True, data=_eData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


