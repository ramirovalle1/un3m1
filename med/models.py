# -*- coding: UTF-8 -*-
import sys

from django.db import models
from django.db.models import Q
from django.db.models import Sum
from settings import PERSONA_ESTADO_CIVIL_ID
from datetime import datetime

from sga.funciones import ModeloBase, null_to_numeric


def med_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                a = eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass


CALIDAD_SUENNO = (('TRANQUILO', 'TRANQUILO'),
                  ('INSOMNIO', 'INSOMNIO'),
                  ('REPARADOR', 'REPARADOR'))

MOTIVO_LENTES = (('', ''),
                 ('ASTIGMATISMO', 'ASTIGMATISMO'),
                 ('MIOPIA', 'MIOPIA'),
                 ('HIPERMETROPIA', 'HIPERMETROPIA'),
                 ('CIRUGIA', 'CIRUGIA'))

TIPO_ALERGIA = (('FARMACOS', 'FARMACOS'),
                ('MEDIO AMBIENTE', 'MEDIO AMBIENTE'),
                ('ALIMENTOS', 'ALIMENTOS'))

FLUJO_MENSTRUAL = (('', ''),
                   ('POCO', 'POCO'),
                   ('NORMAL', 'NORMAL'),
                   ('ABUNDANTE', 'ABUNDANTE'))


TIPO_DROGA = (('OPIACEOS', 'OPIÁCEOS'),
              ('ALUCINOGENOS', 'ALUCINÓGENOS'),
              ('ESTIMULANTES', 'ESTIMULANTES'),
              ('SEDANTES', 'SEDANTES')
              )

FRECUENCIACONSUMO = (
    (1, u"DIARIO"),
    (2, u"SEMANAL"),
    (3, u"MENSUAL"),
)

TABAQUISMO = (('', ''),
              ('MODERADO 5X24h CON FILTRO', 'MODERADO 5X24h CON FILTRO'),
              ('MODERADO 5X24h SIN FILTRO', 'MODERADO 5X24h SIN FILTRO'),
              ('EXAGERADO + 20X24h CON FILTRO', 'EXAGERADO + 20X24h CON FILTRO'),
              ('EXAGERADO + 20X24h SIN FILTRO', 'EXAGERADO + 20X24h SIN FILTRO'))


ALCOHOLISMO = (('', ''),
               ('MODERADO', 'MODERADO'),
               ('ACENTUADO', 'ACENTUADO'),
               ('EXAGERADO', 'EXAGERADO'))

ALIMENTACCION_CANTIDAD = (('', ''),
                          ('CARENCIAL', 'CARENCIAL'),
                          ('NORMAL', 'NORMAL'),
                          ('ABUNDANTE', 'ABUNDANTE'),
                          ('EXCESIVA', 'EXCESIVA'))

ALIMENTACCION_CALIDAD = (('', ''),
                         ('NORMAL', 'NORMAL'),
                         ('RICA EN CARBOHIDRATOS', 'RICA EN CARBOHIDRATOS'),
                         ('EQUILIBRADA', 'EQUILIBRADA'))


VIVIENDA = (('', ''),
            ('PROPIA', 'PROPIA'),
            ('ALQUILADA', 'ALQUILADA'),
            ('FAMILIAR', 'FAMILIAR'))


ZONA = (('', ''),
        ('URBANA', 'URBANA'),
        ('RURAL', 'RURAL'))


TIPO_CONSTRUCCION = (('', ''),
                     ('MADERA', 'MADERA'),
                     ('MIXTA', 'MIXTA'),
                     ('CONCRETO', 'CONCRETO'))


VENTILACION = (('', ''),
               ('ESCASA', 'ESCASA'),
               ('NORMAL', 'NORMAL'),
               ('ABUNDANTE', 'ABUNDANTE'))

AGUA_POTABLE = (('', ''),
                ('TANQUERO', 'TANQUERO'),
                ('TANQUE ELEVADO', 'TANQUE ELEVADO'),
                ('TUBERÍA', 'TUBERÍA'))


LUZ = (('', ''),
       ('ELÉCTRICA', 'ELÉCTRICA'),
       ('CANDIL', 'CANDIL'),
       ('VELA', 'VELA'),
       ('PANEL SOLAR', 'PANEL SOLAR'))


TRANSPORTE = (('', ''),
              ('PROPIO', 'PROPIO'),
              ('PÚBLICO', 'PÚBLICO'))


POSTURA = (('', ''),
           ('DECUBITO DORSAL', 'DECUBITO DORSAL'),
           ('DECUBITO VENTRAL', 'DECUBITO VENTRAL'),
           ('SENTADO', 'SENTADO'),
           ('DE PIE', 'DE PIE'),
           ('INQUIES', 'INQUIES'))

GRADO_ACTIVIDAD = (('', ''),
                   ('ACTIVO', 'ACTIVO'),
                   ('PASIVO', 'PASIVO'))

CRANEO = (('', ''),
          ('NORMOCÉFALO', 'NORMOCÉFALO'),
          ('DOLICOCÉFALO', 'DOLICOCÉFALO'),
          ('MESOCRÁNEO', 'MESOCRÁNEO'),
          ('DOLICRÁNEO', 'DOLICRÁNEO'),
          ('BRAQUICRÁNEO', 'BRAQUICRÁNEO'))

CRANEO_TAMANIO = (('', ''),
                  ('EUENCÉFALO', 'EUENCÉFALO'),
                  ('ARISTENCÉFALO', 'ARISTENCÉFALO'),
                  ('OLIGOENCÉFALO', 'OLIGOENCÉFALO'))

ESTADO_MENTAL = (('', ''),
                 ('LUCIDO', 'LUCIDO'),
                 ('NO LUCIDO', 'NO LUCIDO'))


ESTADO_CARACTER = (('', ''),
                   ('TRANQUILO', 'TRANQUILO'),
                   ('AGRESIVO', 'AGRESIVO'))

FACIES = (('', ''),
          ('TRANQUILO', 'TRANQUILO'),
          ('PREOCUPADO', 'PREOCUPADO'))

BIOTIPO = (('', ''),
           ('PÍCNICO', 'PÍCNICO'),
           ('ASTÉNTICO', 'ASTÉNTICO'),
           ('ATLÉTICO', 'ATLÉTICO'),
           ('DISPLÁSTICO', 'DISPLÁSTICO'),
           ('NORMO TIPO', 'NORMO TIPO'))

TALLA = (('', ''),
         ('NORMAL', 'NORMAL'),
         ('ANORMAL', 'ANORMAL'))

ESTADO_NUTRICIONAL = (('', ''),
                      ('BUENO', 'BUENO'),
                      ('MALO', 'MALO'),
                      ('REGULAR', 'REGULAR'))

LESIONES_TIPO = (('', ''),
                 ('PRIMARIAS', 'PRIMARIAS'),
                 ('SECUNDARIAS', 'SECUNDARIAS'))

MOVIMIENTO = (('', ''),
              ('COORDINADO', 'COORDINADO'),
              ('NO COORDINADO', 'NO COORDINADO'))

TIPO_VEHICULO = (('', ''),
                 ('TAXI', 'TAXI'),
                 ('MOTO', 'MOTO'),
                 ('BUS', 'BUS'),
                 ('BICICLETA', 'BICICLETA'),
                 ('A PIE', 'A PIE'),
                 ('CARRO PROPIO', 'CARRO PROPIO'))

TIEMPO = (('', ''),
          ('DIA', 'DIA'),
          ('NOCHE', 'NOCHE'))

UBICACION = (('', ''),
             ('INSTITUCIÓN', 'INSTITUCIÓN'),
             ('COMERCIO', 'COMERCIO'),
             ('CALLE', 'CALLE'))

FRECUENCIA = (('', ''),
              ('DIARIA', 'DIARIA'),
              ('OCACIONAL', 'OCACIONAL'))


TIPO_PACIENTE = (
    (1, u'ADMINISTRATIVO'),
    (2, u'DOCENTE'),
    (3, u'ESTUDIANTE'),
    (4, u'PARTICULAR'),
    (5, u'PARTICULAR/EPUNEMI'),
    (6, u'TRABAJADOR'),
    (7, u'NIVELACION')
)


ACCION_AREA = (
    (1, u'MEDICA'),
    (2, u'ODONTOLOGICA'),
    (3, u'PSICOLOGICA')
)


ESTADO_REVISION_EXLAB = (
    (1, u'CARGADO'),
    (2, u'VALIDADO'),
    (3, u'RECHAZADO')
)


ACTIVIDAD_FISICA = (
    (1, u'LEVE'),
    (2, u'MODERADA'),
    (3, u'INTENSA')
)

TIPOATENCIONODONTOLOGICA_CHOICES = (
    (1, u'URGENCIA'),
    (2, u'CITA'),
    (3, u'CONSULTA')
)

CAUSAPROFILAXIS_CHOICES = (
    (1, u'MAL CEPILLADO'),
    (2, u'OTRA RAZON')
)

TIPOATENCIONMEDICA_CHOICES = (
    (1, u'PREVENTIVA'),
    (2, u'EMERGENCIA'),
    (3, u'PRIMARIA')
)

TIPOMOVIMIENTOMEDICAMENTO_CHOICES = (
    (1, u'ENTRADA'),
    (2, u'SALIDA')
)

TIPO_CONSERVACION = (
    (1, u'CONSERVACION ADECUADA'),
    (2, u'CONSERVACION INADECUADA')
)

TIPOINVENTARIOMEDICO_CHOICES = (
    (1, u'MEDICAMENTOS'),
    (2, u'MATERIALES')
)


TIPOCONSULTA_CHOICES = (
    (1, u'MÉDICA'),
    (2, u'ODONTOLÓGICA'),
    (3, u'PSICOLÓGICA'),
    (4, u'NUTRICIÓN')
)


TIPOCONSULTA_TERAPIA = (
    (1, u'TERAPIA COGNITIVA'),
    (2, u'TERAPIA INDIVIDUAL'),
    (3, u'TERAPIA DE PAREJA'),
    (4, u'TERAPIA FAMILIAR')
)

GRUPO_SANGRE_CHOICES = (
    ('', ''),
    ('A', 'A'),
    ('B', 'B'),
    ('AB', 'AB'),
    ('O', 'O'),
    # ('RH-', 'RH-'),
    # ('RH+', 'RH+')
)


FACTOR_RH_CHOICES = (
    ('', ''),
    ('RH+', 'RH+'),
    ('RH-', 'RH-')
)

ALTERNATIVAS = (
    (1, u'Muy Buena'),
    (2, u'Buena'),
    (3, u'Mala')
)

ALTERNATIVASVARIAS = (
    (1, u'Mala'),
    (2, u'Regular'),
    (3, u'Buena'),
    (4, u'Muy Buena'),
    (5, u'Excelente')
)

RESPUESTA_HIJOS = (
    (1, u'Pendiente'),
    (2, u'Si'),
    (3, u'No')
)


class PersonaEducacion(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u"Educación")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Nivel educación"
        verbose_name_plural = u"Niveles de educación"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(PersonaEducacion, self).save(*args, **kwargs)


class PersonaProfesion(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u"Profesión")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Profesion"
        verbose_name_plural = u"Profesiones"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(PersonaProfesion, self).save(*args, **kwargs)


class AccionConsulta(ModeloBase):
    descripcion = models.CharField(max_length=150, verbose_name=u"Descripción")
    area = models.IntegerField(choices=ACCION_AREA, blank=True, null=True,verbose_name=u'Area')

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Acción Consulta"
        verbose_name_plural = u"Acciones de Consultas"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(AccionConsulta, self).save(*args, **kwargs)


class CatalogoEnfermedad(ModeloBase):
    clave = models.CharField(max_length=10, verbose_name=u"Clave")
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")
    vigente = models.BooleanField(blank=True, default=False, verbose_name=u'Vigente?')

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Catálogo de Enfermedad"
        verbose_name_plural = u"Catálogo de Enfermedades"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(CatalogoEnfermedad, self).save(*args, **kwargs)

    def flexbox_repr(self):
        return u"%s - %s" % (self.clave, self.descripcion)


class PersonaConsultaMedica(ModeloBase):
    from django.contrib.auth.models import Group
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True,on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha atención")
    medicacion = models.TextField(verbose_name=u'Medicación', blank=True, null=True)
    diagnostico = models.TextField(verbose_name=u'Diagnostico', blank=True, null=True)
    tratamiento = models.TextField(verbose_name=u'Tratamiento', blank=True, null=True)
    medico = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Medico',on_delete=models.CASCADE)
    motivo = models.TextField(verbose_name=u'Motivo', blank=True, null=True)
    pacientegrupo = models.ForeignKey(Group, blank=True, null=True, verbose_name=u'Grupos',on_delete=models.CASCADE)
    tipoatencion = models.IntegerField(choices=TIPOATENCIONMEDICA_CHOICES, default=1, verbose_name=u'Tipo de atención')
    tipopaciente = models.IntegerField(choices=TIPO_PACIENTE, blank=True, null=True,verbose_name=u'Tipo de paciente')
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Matricula',on_delete=models.CASCADE)
    enfermedad = models.ManyToManyField(CatalogoEnfermedad, verbose_name=u'Enfermedades')
    primeravez = models.BooleanField(blank=True, default=False, verbose_name=u'Primera vez')
    accion = models.ManyToManyField(AccionConsulta, verbose_name=u'Acciones realizadas')

    class Meta:
        verbose_name = u"Consulta médica"
        verbose_name_plural = u"Consultas médicas"
        ordering = ['-fecha']
        unique_together = ('persona', 'fecha')

    def __str__(self):
        return u'%s' % self.persona

    def en_fecha(self):
        return self.fecha.date() == datetime.now().date()

    def cantidad_materiales_usados(self):
        return self.inventariomedicomovimiento_set.filter(inventariomedicolote__inventariomedico__tipo=2).count()

    def cantidad_medicamentos_usados(self):
        return self.inventariomedicomovimiento_set.filter(inventariomedicolote__inventariomedico__tipo=1).count()

    def uso_inventario(self):
        return self.inventariomedicomovimiento_set.values('id').exists()

    def productos_usados(self):
        return self.inventariomedicomovimiento_set.all()

    def insumos_utilizados(self):
        return self.inventariomedicomovimiento_set.filter(status=True).order_by('id')

    def tiene_proxima_cita(self):
        return self.proximacita_set.filter(status=True).exists()

    def proxima_cita(self):
        if self.tiene_proxima_cita():
            return self.proximacita_set.filter(status=True)[0]
        return None


class PersonaConsultaOdontologica(ModeloBase):
    from django.contrib.auth.models import Group
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True,on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha atención")
    diagnostico = models.TextField(verbose_name=u'Diagnostico', blank=True, null=True)
    plantratamiento = models.TextField(verbose_name=u'Plan de tratamiento', blank=True, null=True)
    trabajosrealizados = models.TextField(verbose_name=u'Trabajos realizados', blank=True, null=True)
    indicaciones = models.TextField(verbose_name=u'Indicaciones', blank=True, null=True)
    medico = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Medico',on_delete=models.CASCADE)
    motivo = models.TextField(verbose_name=u'Motivo', blank=True, null=True)
    pacientegrupo = models.ForeignKey(Group, blank=True, null=True, verbose_name=u'Grupos',on_delete=models.CASCADE)
    tipoatencion = models.IntegerField(choices=TIPOATENCIONODONTOLOGICA_CHOICES, default=1, verbose_name=u'Tipo de atención')
    profilaxis = models.BooleanField(verbose_name=u'Profilaxis',blank=True, default=False)
    causaprofilaxis = models.IntegerField(choices=CAUSAPROFILAXIS_CHOICES, blank=True, null=True, verbose_name=u'Causa profilaxis')
    tipopaciente = models.IntegerField(choices=TIPO_PACIENTE, blank=True, null=True, verbose_name=u'Tipo de paciente')
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Matricula',on_delete=models.CASCADE)
    enfermedad = models.ManyToManyField(CatalogoEnfermedad, verbose_name=u'Enfermedades')
    primeravez = models.BooleanField(blank=True, default=False, verbose_name=u'Primera vez')
    accion = models.ManyToManyField(AccionConsulta, verbose_name=u'Acciones realizadas')

    class Meta:
        verbose_name = u"Consulta odontológica"
        verbose_name_plural = u"Consultas odontológicas"
        ordering = ['-fecha']
        unique_together = ('persona', 'fecha')

    def __str__(self):
        return u'%s' % self.persona

    def en_fecha(self):
        return self.fecha.date() == datetime.now().date()

    def cantidad_materiales_usados(self):
        return self.inventariomedicomovimiento_set.values('id').filter(inventariomedicolote__inventariomedico__tipo=2).count()

    def cantidad_medicamentos_usados(self):
        return self.inventariomedicomovimiento_set.values('id').filter(inventariomedicolote__inventariomedico__tipo=1).count()

    def uso_inventario(self):
        return self.inventariomedicomovimiento_set.values('id').exists()

    def productos_usados(self):
        return self.inventariomedicomovimiento_set.all()


class PersonaConsultaPsicologica(ModeloBase):
    from django.contrib.auth.models import Group
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True,on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha atención")
    medicacion = models.TextField(verbose_name=u'Medicación', blank=True, null=True)
    diagnostico = models.TextField(verbose_name=u'Diagnostico', blank=True, null=True)
    tratamiento = models.TextField(verbose_name=u'Tratamiento', blank=True, null=True)
    medico = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Medico',on_delete=models.CASCADE)
    motivo = models.TextField(verbose_name=u'Motivo', blank=True, null=True)
    pacientegrupo = models.ForeignKey(Group, blank=True, null=True, verbose_name=u'Grupos',on_delete=models.CASCADE)
    tipoatencion = models.IntegerField(choices=TIPOATENCIONMEDICA_CHOICES, default=1, verbose_name=u'Tipo de atención')
    tipoterapia = models.IntegerField(choices=TIPOCONSULTA_TERAPIA, default=1, verbose_name=u'Tipo de terapia')
    tipopaciente = models.IntegerField(choices=TIPO_PACIENTE, blank=True, null=True, verbose_name=u'Tipo de paciente')
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Matricula',on_delete=models.CASCADE)
    enfermedad = models.ManyToManyField(CatalogoEnfermedad, verbose_name=u'Enfermedades')
    primeravez = models.BooleanField(blank=True, default=False, verbose_name=u'Primera vez')
    accion = models.ManyToManyField(AccionConsulta, verbose_name=u'Acciones realizadas')

    class Meta:
        verbose_name = u"Consulta Psicológica"
        verbose_name_plural = u"Consultas Psicológicas"
        ordering = ['-fecha']
        unique_together = ('persona', 'fecha')

    def __str__(self):
        return u'%s' % self.persona

    def en_fecha(self):
        return self.fecha.date() == datetime.now().date()

    def cantidad_materiales_usados(self):
        return self.inventariomedicomovimiento_set.values('id').filter(inventariomedicolote__inventariomedico__tipo=2).count()

    def cantidad_medicamentos_usados(self):
        return self.inventariomedicomovimiento_set.values('id').filter(inventariomedicolote__inventariomedico__tipo=1).count()

    def uso_inventario(self):
        return self.inventariomedicomovimiento_set.values('id').exists()

    def productos_usados(self):
        return self.inventariomedicomovimiento_set.all()


class PersonaConsultaNutricion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True,on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha atención")
    motivo = models.TextField(verbose_name=u'Motivo', blank=True, null=True)
    diagnostico = models.TextField(verbose_name=u'Diagnostico', blank=True, null=True)
    recomendacion = models.TextField(verbose_name=u'recomendacion', blank=True, null=True)
    medico = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Medico',on_delete=models.CASCADE)
    tipopaciente = models.IntegerField(choices=TIPO_PACIENTE, blank=True, null=True, verbose_name=u'Tipo de paciente')
    actividadfisica = models.IntegerField(choices=ACTIVIDAD_FISICA, blank=True, null=True, verbose_name=u'Actividad física')
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Matricula',on_delete=models.CASCADE)
    primeravez = models.BooleanField(blank=True, default=False, verbose_name=u'Primera vez')
    tipoatencion = models.IntegerField(choices=TIPOATENCIONODONTOLOGICA_CHOICES, default=3, verbose_name=u'Tipo de atención')
    importado = models.BooleanField(blank=True, default=False, verbose_name=u'Registro importado')
    lleno = models.BooleanField(blank=True, default=False, verbose_name=u'Registro llenado')


    class Meta:
        verbose_name = u"Consulta de Nutrición"
        verbose_name_plural = u"Consultas de Nutrición"
        ordering = ['-fecha']
        unique_together = ('persona', 'fecha')

    def en_fecha(self):
        return self.fecha.date() == datetime.now().date()

    def consultaantropometria(self):
        return self.consultanutricionantropometria_set.filter(status=True)

    def consultaenfermedad(self):
        return self.enfermedadpersonaconsultanutricion_set.filter(status=True)

    def __str__(self):
        return u'%s' % self.persona


class EnfermedadPersonaConsultaNutricion(ModeloBase):
    consulta = models.ForeignKey(PersonaConsultaNutricion, verbose_name=u'Persona consulta',on_delete=models.CASCADE)
    enfermedad = models.ForeignKey(CatalogoEnfermedad, verbose_name=u'Enfermedad',on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.consulta


class ProximaCita(ModeloBase):
    consultamedica = models.ForeignKey(PersonaConsultaMedica, verbose_name=u'Consulta Médica', blank=True, null=True, on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha y hora de la Cita")
    medico = models.ForeignKey('sga.Persona', related_name='medico', verbose_name=u'Médico',on_delete=models.CASCADE)
    indicaciones = models.CharField(max_length=300, verbose_name=u'Indicaciones', blank=True, null=True)
    asistio = models.BooleanField(blank=True,default=False, verbose_name=u'Asistió')
    tipoconsulta = models.IntegerField(choices=TIPOCONSULTA_CHOICES, default=1, verbose_name=u'Tipo de consulta')

    def __str__(self):
        return "%s" % self.persona

    class Meta:
        verbose_name = u"Próxima cita"
        verbose_name_plural = u"Proximas citas"
        ordering = ['-fecha']
        unique_together = ('persona', 'fecha')

    def vigente(self):
        return datetime.now().date() <= self.fecha.date()

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return ProximaCita.objects.filter(Q(indicaciones__contains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return self.persona.nombre_completo() + ' - ' + self.fecha.strftime("%d-%m-%Y") + self.id.__str__()

    def save(self, *args, **kwargs):
        self.indicaciones = self.indicaciones.upper() if self.indicaciones else ''
        super(ProximaCita, self).save(*args, **kwargs)


class PersonaExtension(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u"Persona",on_delete=models.CASCADE)
    estadocivil = models.ForeignKey('sga.PersonaEstadoCivil', related_name=u'estadocivil', blank=True, null=True, verbose_name=u"Estado civil",on_delete=models.CASCADE)
    tienelicencia = models.BooleanField(default=False,verbose_name=u'Licencia de conducción')
    tipolicencia = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Tipo de licencia')
    telefonos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"Telefonos de familiar")
    tieneconyuge = models.BooleanField(default=False,verbose_name=u"Conyuge")
    tienehijos = models.IntegerField(choices=RESPUESTA_HIJOS, default=1, verbose_name=u'Respondió pregunta hijos')
    # 1. ya no se utilizaran
    enfermedadpadre = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Enfermedades del padre')
    enfermedadmadre = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Enfermedades de la madre')
    enfermedadabuelos = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Enfermedades de abuelos')
    enfermedadhermanos = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Enfermedades de hermanos')
    enfermedadotros = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Enfermedades de otros integrantes')
    # 1.
    #nuevos
    hijos = models.IntegerField(blank=True, null=True, verbose_name=u'No. hijos')
    edadaparenta = models.IntegerField(blank=True, null=True, verbose_name=u'Edad que Aparenta')
    horanacimiento = models.TimeField(verbose_name=u'Hora de Nacimiento', blank=True, null=True)
    #
    contactoemergencia = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Contacto de emergencia')
    telefonoemergencia = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Telefono de emergencia')
    correoemergencia = models.CharField(default='', max_length=200, blank=True, null=True, verbose_name=u'Correo de emergencia')
    telefonoconvemergencia = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Teléfono convencional de emergencia')
    parentescoemergencia = models.ForeignKey('sga.ParentescoPersona', blank=True, null=True, verbose_name=u"Parentesco",on_delete=models.CASCADE)
    carnetiess = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Carnet IESS')

    cedularepsolidario = models.CharField(blank=True, null=True, max_length=20, verbose_name=u"Cedula Representante Solidario")
    nombresrepsolidario = models.CharField(blank=True, null=True, max_length=100, verbose_name=u'Nombre Representante Solidario')
    apellido1repsolidario = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"1er Apellido Representante Solidario")
    apellido2repsolidario = models.CharField(blank=True, null=True, max_length=50, verbose_name=u"2do Apellido Representante Solidario")

    class Meta:
        verbose_name = u"Informacion Medica"
        verbose_name_plural = u"Informaciones Medicas"
        unique_together = ('persona',)

    def personafichamedica(self):
        if self.personafichamedica_set.values('id').exists():
            pfm = self.personafichamedica_set.all()[0]
        else:
            pfm = PersonaFichaMedica(personaextension=self)
            pfm.save()
        return pfm

    def personaexamenfisico(self):
        fm = self.personafichamedica()
        if fm.personaexamenfisico_set.values('id').exists():
            pef = fm.personaexamenfisico_set.all()[0]
        else:
            pef = PersonaExamenFisico(personafichamedica=fm)
            pef.save()
        return pef

    def personadatospsicologico(self):
        fm = self.personafichamedica()
        if fm.datospsicologico_set.values('id').exists():
            pef = fm.datospsicologico_set.all()[0]
        else:
            pef = DatosPsicologico(personafichamedica=fm)
            pef.save()
        return pef

    def save(self, *args, **kwargs):
        self.tipolicencia = self.tipolicencia.upper().strip() if self.tipolicencia else ''
        self.enfermedadpadre = self.enfermedadpadre.upper().strip() if self.enfermedadpadre else ''
        self.enfermedadmadre = self.enfermedadmadre.upper().strip() if self.enfermedadmadre else ''
        self.enfermedadabuelos = self.enfermedadabuelos.upper().strip() if self.enfermedadabuelos else ''
        self.enfermedadhermanos = self.enfermedadhermanos.upper().strip() if self.enfermedadhermanos else ''
        self.enfermedadotros = self.enfermedadotros.upper().strip() if self.enfermedadotros else ''
        self.contactoemergencia = self.contactoemergencia.upper().strip() if self.contactoemergencia else ''
        self.telefonoemergencia = self.telefonoemergencia.upper().strip() if self.telefonoemergencia else ''
        if not self.estadocivil:
            self.estadocivil_id = PERSONA_ESTADO_CIVIL_ID
        super(PersonaExtension, self).save(*args, **kwargs)


class PersonaFichaMedica(ModeloBase):
    personaextension = models.ForeignKey(PersonaExtension, verbose_name=u"Persona",on_delete=models.CASCADE)
    vacunas = models.BooleanField(default=False,verbose_name=u'Vacunas básicas completas?') # eliminar despues pasar a PatologicoPersonal
    nombrevacunas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Vacunas') # eliminar despues pasar a PatologicoPersonal
    enfermedades = models.BooleanField(default=False,verbose_name=u'Enfermedades crónicas?') # eliminar ....
    nombreenfermedades = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Enfermedades') # eliminar despues pasar a PatologicoPersonal
    alergiamedicina = models.BooleanField(default=False,verbose_name=u'Alergias a medicinas?') # eliminar ...
    nombremedicinas = models.CharField(max_length=100, verbose_name=u'Medicinas', blank=True, null=True) # eliminar ...
    alergiaalimento = models.BooleanField(default=False,verbose_name=u'Alergias o intoxicación con alimentos?') #Eliminar ....
    nombrealimentos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Alimentos') #Eliminar ....
    cirugias = models.BooleanField(default=False,verbose_name=u'Cirugías?')
    nombrecirugia = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Organo comprometido')
    fechacirugia = models.DateField(blank=True, verbose_name=u'Fecha ultima operación', null=True)
    aparato = models.BooleanField(default=False,verbose_name=u'Aparatos ortopédicos?')
    tipoaparato = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Tipo aparato ortopédico')

    gestacion = models.BooleanField(default=False,verbose_name=u'Gestación actual?')
    partos = models.IntegerField(blank=True, null=True, verbose_name=u'No. partos')
    abortos = models.IntegerField(blank=True, null=True, verbose_name=u'No. abortos')
    cesareas = models.IntegerField(blank=True, null=True, verbose_name=u'No. cesareas')
    hijos2 = models.IntegerField(blank=True, null=True, verbose_name=u'No. hijos')

    cigarro = models.BooleanField(default=False,verbose_name=u'Cigarrillo?')
    numerocigarros = models.IntegerField(blank=True, null=True, verbose_name=u'No. cigarrillos por día')
    tomaalcohol = models.BooleanField(default=False,verbose_name=u'Bebidas alcoholicas?')
    tipoalcohol = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Tipo de bebidas')
    copasalcohol = models.IntegerField(blank=True, null=True, verbose_name=u'No. copas a la semana')
    tomaantidepresivos = models.BooleanField(default=False,verbose_name=u'Antidepresivos?')
    antidepresivos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Especifique antidepresivos')
    tomaotros = models.BooleanField(default=False,verbose_name=u'Otros?')
    otros = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Especifique otros')
    horassueno = models.IntegerField(blank=True, null=True, verbose_name=u'No. horas de sueño')
    calidadsuenno = models.CharField(max_length=30, choices=CALIDAD_SUENNO, blank=True, null=True, verbose_name=u"Cantidad horas de sueño")

    probcardiacos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Problemas cardiacos')
    presionalterial = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Presion arterial')
    enfermedadesvenereas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Enfermedades venereas')
    fiebrereumatica = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Fiebre reumatica')
    hepatitis = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Hepatitis')
    ulceragastrica = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Ulcera gastrica')
    diabetis = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Diabetis')
    epilepsia = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Epilepsia')
    sinusitis = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Sinusitis')
    enfermedadesnerviosas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Enfermedades nerviosas')
    enfermedadescongenitas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Enfermedades congenitas')
    otras = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Otras')
    habitoshigienicos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Habitos higienicos')
    frecuenciacepillado = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Frecuencia cepillado')
    consumegolosinas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Consume golosinas')
    hospitalizado = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    ultimahospitalizacion = models.DateField(blank=True, null=True, verbose_name=u"Fecha ultima hospitalización")
    motivo = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Motivo')
    aparatodigestivo = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Aparato digestivo')
    atm_ruidos = models.BooleanField(default=False, verbose_name=u'Ruidos')
    atm_lateralidad = models.BooleanField(blank=True,default=False, verbose_name=u'Lateralidad')
    atm_apertura = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    atm_chasquidos = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    atm_crepitacion = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    atm_dificultadapertura = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    atm_fatigadolor = models.BooleanField(blank=True,default=False, verbose_name=u'Hospitalizado?')
    atm_disminucionabertura = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    atm_desviacionabertura = models.BooleanField(default=False, verbose_name=u'Hospitalizado?')
    tb_glanglios = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Glanglios')
    tb_glandulassalibares = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Glandulas salibares')
    tb_labios = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Labios')
    tb_comisuras = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Comisuras')
    tb_carrillos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Carillos')
    tb_fondosaco = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Fondo de saco')
    tb_frenillos = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Frenillos')
    tb_lenguaterciomedio = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Lengua tercio medio')
    tb_paladarduro = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Paladar duro')
    tb_paladarblando = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Paladar blando')
    tb_istmo = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Istmo')
    tb_bucofaringe = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Bucofaringe')
    tb_lengua = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Lengua')
    tb_pisoboca = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Pisoboca')
    tb_dientes = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Dientes')
    tb_mucosaalveolar = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Mucosa del borde alveolar')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha ficha médica')
    archivoexamenlaboratorio = models.FileField(blank=True, null=True, upload_to='documentos/%Y/%m/%d',verbose_name=u'Archivo resultado examen laboratorio')
    estadorevisionexlab = models.IntegerField(choices=ESTADO_REVISION_EXLAB, blank=True, null=True, verbose_name=u'Estado de revisión del examen')
    observacionexlab = models.TextField(verbose_name=u'Observación de revisión', blank=True, null=True)

    class Meta:
        verbose_name = u"Ficha Medica"
        verbose_name_plural = u"Fichas Medicas"
        unique_together = ('personaextension',)

    def odontograma(self):
        if self.odontograma_set.values('id').exists():
            odontograma = self.odontograma_set.all()[0]
        else:
            odontograma = Odontograma(fichamedica=self)
            odontograma.save()
        return odontograma

    def save(self, *args, **kwargs):
        self.partos = self.partos if self.partos else 0
        self.abortos = self.abortos if self.abortos else 0
        self.cesareas = self.cesareas if self.cesareas else 0
        self.hijos2 = self.hijos2 if self.hijos2 else 0
        self.horassueno = self.horassueno if self.horassueno else 0
        self.copasalcohol = self.copasalcohol if self.copasalcohol else 0
        self.nombrevacunas = self.nombrevacunas.upper().strip() if self.nombrevacunas else ''
        self.nombreenfermedades = self.nombreenfermedades.upper().strip() if self.nombreenfermedades else ''
        self.nombremedicinas = self.nombremedicinas.upper().strip() if self.nombremedicinas else ''
        self.nombrealimentos = self.nombrealimentos.upper().strip() if self.nombrealimentos else ''
        self.nombrecirugia = self.nombrecirugia.upper().strip() if self.nombrecirugia else ''
        self.tipoaparato = self.tipoaparato.upper().strip() if self.tipoaparato else ''
        self.tipoalcohol = self.tipoalcohol.upper().strip() if self.tipoalcohol else ''
        self.antidepresivos = self.antidepresivos.upper().strip() if self.antidepresivos else ''
        self.otros = self.otros.upper().strip() if self.otros else ''
        super(PersonaFichaMedica, self).save(*args, **kwargs)


class Vacuna(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Vacuna"
        verbose_name_plural = u"Vacunas"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Vacuna, self).save(*args, **kwargs)


class Alergia(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")
    tipo = models.CharField(max_length=30, choices=TIPO_ALERGIA, verbose_name=u"Tipo Alergia")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Alergia"
        verbose_name_plural = u"Alergias"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Alergia, self).save(*args, **kwargs)


class Medicina(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Medicina"
        verbose_name_plural = u"Medicinas"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Medicina, self).save(*args, **kwargs)


class TipoEnfermedad(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Tipo Enfermedad"
        verbose_name_plural = u"Tipo Enfermedades"
        unique_together = ('descripcion',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('TipoEnfermedad.objects.filter(Q(descripcion__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return TipoEnfermedad.objects.filter(Q(descripcion__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.descripcion

    def flexbox_alias(self):
        return [self.id, self.descripcion.upper()]

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(TipoEnfermedad, self).save(*args, **kwargs)

    def puede_eliminar(self):
        return not self.enfermedad_set.values("id").all().exists()


class Enfermedad(ModeloBase):
    tipo = models.ForeignKey(TipoEnfermedad, verbose_name=u"Tipo Enfermedades",on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")
    hereditaria = models.BooleanField(default=False, verbose_name=u'¿Enfermedad es hereditaria?')
    # 1.INFANTIL 2.GENERAL 3.VISUAL 4.VENEREAS

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Enfermedad"
        verbose_name_plural = u"Enfermedades"
        unique_together = ('descripcion',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval('Enfermedad.objects.filter(Q(descripcion__icontains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        return Enfermedad.objects.filter(Q(descripcion__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.descripcion

    def flexbox_alias(self):
        return [self.id, self.descripcion.upper()]

    def puede_eliminar(self):
        return not self.personaenfermedad_set.values("id").all().exists()

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Enfermedad, self).save(*args, **kwargs)


class Parentesco(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Parentesco"
        verbose_name_plural = u"Parentescos"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Parentesco, self).save(*args, **kwargs)


class Cirugia(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Cirugia"
        verbose_name_plural = u"Cirugias"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Cirugia, self).save(*args, **kwargs)


class PatologicoFamiliar(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    parentesco = models.ForeignKey(Parentesco, verbose_name=u'Parentesco',on_delete=models.CASCADE)
    paterno = models.BooleanField(blank=True,verbose_name=u'Es Paterno?')
    enfermedades = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades')

    def __str__(self):
        return u"%s" % self.parentesco

    class Meta:
        verbose_name = u"Patologico Familiar"
        verbose_name_plural = u"Patologicos Familiares"

    def save(self, *args, **kwargs):
        super(PatologicoFamiliar, self).save(*args, **kwargs)


class PatologicoPersonal(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    nacio = models.BooleanField(blank=True,verbose_name=u'Nació a término?')
    partonormal = models.BooleanField(blank=True,verbose_name=u'Parto Normal?')
    partocesarea = models.BooleanField(blank=True,verbose_name=u'Cesárea?')
    partocomplicacion = models.CharField(blank=True, null=True,max_length=200,  verbose_name=u'Complicaciones en Parto')
    lactanciamaterna = models.BooleanField(blank=True,verbose_name=u'Lactancia Materna?')
    lactanciaartificial = models.BooleanField(blank=True,verbose_name=u'Lactancia Artificial?')
    ablactacion = models.CharField(max_length=2, blank=True, null=True, verbose_name=u'Ablactación / Meses')
    enfermedadinfancia = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades de la Infancia', related_name='enfermedadinfancia')
    letes = models.BooleanField(blank=True,verbose_name=u'Usa lentes?')
    enfermedadvisual = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades Visuales', related_name='enfermedadvisual')
    vacuna = models.BooleanField(blank=True,verbose_name=u'Vacunas?')
    vacunas = models.ManyToManyField(Vacuna, verbose_name=u'Vacunas')
    transfusion = models.BooleanField(blank=True,verbose_name=u'Transfusiones?')
    gruposangre = models.CharField(max_length=10, choices=GRUPO_SANGRE_CHOICES, blank=True, null=True, verbose_name=u"Grupo Sangre") # tambien eliminar
    factorrh = models.CharField(max_length=10, choices=FACTOR_RH_CHOICES, blank=True, null=True, verbose_name=u"Factor RH")
    alergiamedicina = models.BooleanField(blank=True,verbose_name=u'Alergia a Medicinas?')
    alergiamedicinas = models.ManyToManyField(Alergia, verbose_name=u'Medicinas', related_name='alergiamedicinas')
    alergiaambiente = models.BooleanField(blank=True,verbose_name=u'Alergia a Sustancias Ambiente?')
    alergiaambientes = models.ManyToManyField(Alergia, verbose_name=u'Sustancias Ambiente', related_name='alergiaambientes')
    alergiaalimento = models.BooleanField(blank=True,verbose_name=u'Alergia por Alimientos?')
    alergiaalimentos = models.ManyToManyField(Alergia, verbose_name=u'Alimentos', related_name='alergiaalimentos')
    tomamedicina = models.BooleanField(blank=True,verbose_name=u'Toma Medicina?')

    medicinas = models.ManyToManyField(Medicina, verbose_name=u'Medicinas', related_name='medicinas')

    enfermedad = models.BooleanField(blank=True,verbose_name=u'Enfermedades?')
    enfermedades = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades', related_name='enfermedades')
    enfermedadtrabajo = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades Durante el Trabajo', related_name='enfermedadtrabajo')
    enfermedadvenerea = models.BooleanField(blank=True,verbose_name=u'Enfermedad Venérea?')
    enfermedadvenereas = models.ManyToManyField(Enfermedad, verbose_name=u'Enfermedades Venéreas', related_name='enfermedadvenereas')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Patologico Personal"
        verbose_name_plural = u"Patologicos Personales"

    def save(self, *args, **kwargs):
        super(PatologicoPersonal, self).save(*args, **kwargs)


class PatologicoQuirurgicos(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    cirugia = models.BooleanField(blank=True,verbose_name=u'Cirugías?')
    cirugias = models.ManyToManyField(Cirugia, verbose_name=u'Cirugias')
    fechacirugia = models.DateField(blank=True, null=True, verbose_name=u'Fecha ultima operación')
    complicacion = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Complicaciones')
    establecimiento = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'En que Establecimiento')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Patologico Quirurgico"
        verbose_name_plural = u"Patologicos Quirurgicos"

    def save(self, *args, **kwargs):
        self.complicacion = self.complicacion.upper().strip() if self.complicacion else ''
        self.establecimiento = self.establecimiento.upper().strip() if self.establecimiento else ''
        super(PatologicoQuirurgicos, self).save(*args, **kwargs)


class LugarAnatomico(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Lugar Anatomico"
        verbose_name_plural = u"Lugares Anatomico"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(LugarAnatomico, self).save(*args, **kwargs)


class AntecedenteTraumatologicos(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    fractura = models.BooleanField(blank=True,verbose_name=u'Fracturas?')
    lugaranatomico = models.ManyToManyField(LugarAnatomico, verbose_name=u'Lugar Anatomico')
    accidentelaboral = models.BooleanField(blank=True,verbose_name=u'Accidente Laboral?')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Antecedente Traumatologicos"
        verbose_name_plural = u"Antecedentes Traumatologicos"

    def save(self, *args, **kwargs):
        super(AntecedenteTraumatologicos, self).save(*args, **kwargs)


class MetodoAnticonceptivo(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Metodo Anticonceptivo"
        verbose_name_plural = u"Metodos Anticonceptivos"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(MetodoAnticonceptivo, self).save(*args, **kwargs)


class AntecedenteGinecoobstetrico(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    flujomenstrual = models.CharField(max_length=10, choices=FLUJO_MENSTRUAL, blank=True, null=True, verbose_name=u"Flujo Menstrual")
    menarquia = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Menarquia / Edad')
    catamenial = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Indice Catamenial')
    embrazos = models.BooleanField(blank=True,verbose_name=u'Embrazos?')
    partos = models.IntegerField(blank=True, null=True, verbose_name=u'No. partos')
    partonormal = models.BooleanField(blank=True,verbose_name=u'Parto Normal?')
    partoprematuro = models.BooleanField(blank=True,verbose_name=u'Parto Prematuro?')
    cesareas = models.IntegerField(blank=True, null=True, verbose_name=u'No. cesareas')
    hijosvivos = models.IntegerField(blank=True, null=True, verbose_name=u'No. hijos Vivos')
    abortos = models.IntegerField(blank=True, null=True, verbose_name=u'No. abortos')
    abortonatural = models.BooleanField(blank=True,verbose_name=u'Causas Naturales?')
    abortoprovocado = models.BooleanField(blank=True,verbose_name=u'Provocado?')
    legrado = models.BooleanField(blank=True,verbose_name=u'Legrados?')
    puerperiocomplicacion = models.CharField(max_length=200, blank=True, null=True, verbose_name=u'Puerperios y Complicaciones')
    anticonceptivo = models.BooleanField(blank=True,verbose_name=u'Anticonceptivos?')
    metodoanticonceptivo = models.ManyToManyField(MetodoAnticonceptivo, verbose_name=u'Metodos Anticonceptivos')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Antecedente Ginecoobstetrico"
        verbose_name_plural = u"Antecedentes Ginecoobstetrico"

    def save(self, *args, **kwargs):
        self.puerperiocomplicacion = self.puerperiocomplicacion.upper().strip() if self.puerperiocomplicacion else ''
        super(AntecedenteGinecoobstetrico, self).save(*args, **kwargs)


class Droga(ModeloBase):
    tipo = models.CharField(max_length=120, choices=TIPO_DROGA, verbose_name=u"Tipo")
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Droga"
        verbose_name_plural = u"Drogas"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Droga, self).save(*args, **kwargs)


class Habito(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    cafecantidad = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Cafeísmo Cantidad')
    cafecalidad = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Calidad')
    cafefrecuencia = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Frecuencia')
    teismocantidad = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Teísmo CAntidad')
    tecalidad = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Calidad')
    tefrecuencia = models.CharField(max_length=20, blank=True, null=True, verbose_name=u'Frecuencia')

    consumetabaco = models.BooleanField(blank=True, default=False, verbose_name=u'Consume tabaco?')
    tabaquismo = models.CharField(max_length=120, choices=TABAQUISMO, blank=True, null=True, verbose_name=u"Tabaquismo")

    consumealcohol = models.BooleanField(blank=True, default=False, verbose_name=u'Consume alcohol?')
    alcoholismo = models.CharField(max_length=100, choices=ALCOHOLISMO, blank=True, null=True, verbose_name=u"Alcoholismo")

    consumedroga = models.BooleanField(blank=True, default=False, verbose_name=u'Consume drogas?')
    droga = models.ManyToManyField(Droga, verbose_name=u'Drogas')

    alimentocantidad = models.CharField(max_length=30, choices=ALIMENTACCION_CANTIDAD, blank=True, null=True, verbose_name=u'Alimentación Cantidad')
    alimentocalidad = models.CharField(max_length=30, choices=ALIMENTACCION_CALIDAD, blank=True, null=True, verbose_name=u'Calidad')

    remuneracion = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u"Remuneración")
    cargafamiliar = models.IntegerField(blank=True, null=True, verbose_name=u'Cargas Familiar')
    manutencion = models.BooleanField(blank=True,verbose_name=u'Pago de manutención de niños?')
    vivienda = models.CharField(max_length=20, choices=VIVIENDA, blank=True, null=True, verbose_name=u'Vivienda')
    zona = models.CharField(max_length=20, choices=ZONA, blank=True, null=True, verbose_name=u'Zona')
    tipoconstruccion = models.CharField(max_length=20, choices=TIPO_CONSTRUCCION, blank=True, null=True, verbose_name=u'Tipo Construccion')
    ventilacion = models.CharField(max_length=20, choices=VENTILACION, blank=True, null=True, verbose_name=u'Ventilación')
    numeropersonas = models.IntegerField(blank=True, null=True, verbose_name=u'No. Personas')
    animalesdomesticos = models.BooleanField(blank=True,verbose_name=u'Animales Domesticos?')
    animalclase = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Clase de Animal')
    animalcantidad = models.IntegerField(blank=True, null=True, verbose_name=u'No. Animales')
    servicioshigienicos = models.IntegerField(blank=True, null=True, verbose_name=u'No. Servicios Higiénicos')
    aguapotable = models.CharField(max_length=20, choices=AGUA_POTABLE, blank=True, null=True, verbose_name=u'Agua Potable')
    luz = models.CharField(max_length=20, choices=LUZ, blank=True, null=True, verbose_name=u'Luz')
    transporte = models.CharField(max_length=20, choices=TRANSPORTE, blank=True, null=True, verbose_name=u'Transporte')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Habito"
        verbose_name_plural = u"Habitos"

    def droga_opiaceos(self):
        return self.droga.filter(tipo='OPIACEOS')

    def droga_alucinogenos(self):
        return self.droga.filter(tipo='ALUCINOGENOS')

    def droga_estimulante(self):
        return self.droga.filter(tipo='ESTIMULANTES')

    def droga_sedantes(self):
        return self.droga.filter(tipo='SEDANTES')


class AntecedenteOdontologico(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha ficha odontologica')
    bajotratamiento = models.BooleanField(blank=True, default=False, verbose_name=u'Bajo tratamiento odontológico?')
    esalergico = models.BooleanField(blank=True, verbose_name=u'Alergia a Medicina u otra cosa?')
    alergias = models.ManyToManyField(Alergia, verbose_name=u'Medicinas')
    propensohemorragia = models.BooleanField(blank=True, default=False, verbose_name=u'Propenso a hemorragia?')
    complicacionanestesiaboca = models.BooleanField(blank=True, default=False, verbose_name=u'Complicaciones por aplicación de anestesia en boca?')
    toperatoria = models.BooleanField(blank=True, default=False, verbose_name=u'Tratamiento operatoria?')
    tperiodoncia = models.BooleanField(blank=True, default=False, verbose_name=u'Tratamiento periodoncia?')
    totro = models.BooleanField(blank=True, default=False, verbose_name=u'Tratamiento otros?')
    periodontal = models.BooleanField(blank=True, default=False, verbose_name=u'Enfermedad periodontal?')
    materiaalba = models.BooleanField(blank=True, default=False, verbose_name=u'Materia alba?')
    placabacteriana = models.BooleanField(blank=True, default=False, verbose_name=u'Placa bacteriana?')
    calculossupra = models.BooleanField(blank=True, default=False, verbose_name=u'Cálculos suprangingival-subgingival?')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Antecedente Odontologico"
        verbose_name_plural = u"Antecedentes Odontologicos"


class Odontograma(ModeloBase):
    fichamedica = models.ForeignKey(PersonaFichaMedica, verbose_name=u"Ficha medica",on_delete=models.CASCADE)
    pieza_11 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_12 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_13 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_14 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_15 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_16 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_17 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_18 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 11")
    pieza_21 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 21")
    pieza_22 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 22")
    pieza_23 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 23")
    pieza_24 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 24")
    pieza_25 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 25")
    pieza_26 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 26")
    pieza_27 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 27")
    pieza_28 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 28")
    pieza_51 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 51")
    pieza_52 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 52")
    pieza_53 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 53")
    pieza_54 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 54")
    pieza_55 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 55")
    pieza_61 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 61")
    pieza_62 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 62")
    pieza_63 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 63")
    pieza_64 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 64")
    pieza_65 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 65")
    pieza_71 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 71")
    pieza_72 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 72")
    pieza_73 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 73")
    pieza_74 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 74")
    pieza_75 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 75")
    pieza_81 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 81")
    pieza_82 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 82")
    pieza_83 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 83")
    pieza_84 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 84")
    pieza_85 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 85")
    pieza_31 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 31")
    pieza_32 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 32")
    pieza_33 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 33")
    pieza_34 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 34")
    pieza_35 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 35")
    pieza_36 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 36")
    pieza_37 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 37")
    pieza_38 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 38")
    pieza_41 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 41")
    pieza_42 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 42")
    pieza_43 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 43")
    pieza_44 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 44")
    pieza_45 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 45")
    pieza_46 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 46")
    pieza_47 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 47")
    pieza_48 = models.CharField(default="00000", max_length=5, verbose_name=u"Pieza 48")
    placaactual = models.IntegerField(default=0, verbose_name=u"Placa actual")

    class Meta:
        unique_together = ('fichamedica',)


class IndicadorSobrepeso(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Indicadores')
    minimohombre = models.FloatField(default=0, verbose_name=u'Minimo hombre')
    maximohombre = models.FloatField(default=0, verbose_name=u'Maximo hombre')
    minimomujer = models.FloatField(default=0, verbose_name=u'Minimo mujer')
    maximomujer = models.FloatField(default=0, verbose_name=u'Maximo mujer')

    def __str__(self):
        return u'%s - (H de %s a %s), (M de %s a %s)' % (self.nombre, self.minimohombre, self.maximohombre, self.minimomujer, self.maximomujer)

    def nombre_simple(self):
        return self.nombre if self.nombre else ""

    class Meta:
        verbose_name = u'Indicador de sobrepeso'
        verbose_name_plural = u'Indicadores de sobrepeso'
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip() if self.nombre else ''
        if self.minimohombre > self.maximohombre or self.minimomujer > self.maximomujer:
            raise NameError('Error')
        super(IndicadorSobrepeso, self).save(*args, **kwargs)


class PersonaExamenFisico(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, verbose_name=u"Ficha medica",on_delete=models.CASCADE)
    inspeccion = models.TextField(blank=True, null=True, verbose_name=u'Observación general del estudiante') #Eliminar despues
    usalentes = models.BooleanField(default=False,verbose_name=u'Usa lentes?')  #Eliminar despues de pasar este valor a ficha medica
    motivo = models.CharField(max_length=100, choices=MOTIVO_LENTES, blank=True, null=True, verbose_name=u"Motivo") # tambien eliminar
    peso = models.FloatField(default=0, verbose_name=u'Peso')
    talla = models.FloatField(default=0, verbose_name=u'Talla')
    pa = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Presión arterial')
    pulso = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Pulso')
    rcar = models.CharField(max_length=50, blank=True, null=True, verbose_name=u'Ritmo cardiacos')
    rresp = models.FloatField(default=0, verbose_name=u'Ritmo respiratorio')
    temp = models.FloatField(default=0, verbose_name=u'Temperatura')
    observaciones = models.TextField(default='', verbose_name=u'Observación (especificar limitantes si existen)')
    indicecorporal = models.FloatField(default=0, verbose_name=u'Indice Corporal')
    indicadorsobrepeso = models.ForeignKey(IndicadorSobrepeso, blank=True, null=True, verbose_name=u'Indicador sobrepeso',on_delete=models.CASCADE)

    class Meta:
        verbose_name = u"Examen Fisico"
        verbose_name_plural = u"Examenenes Fisicos"
        unique_together = ('personafichamedica',)

    def indice_corporal(self):
        return round(self.peso / self.talla ** 2, 2) if self.talla else 0

    def indicador_sobrepeso(self):
        ic = self.indice_corporal()
        if self.personafichamedica.personaextension.persona.es_mujer():
            if IndicadorSobrepeso.objects.values('id').filter(minimomujer__lte=ic, maximomujer__gte=ic).exists():
                return IndicadorSobrepeso.objects.filter(minimomujer__lte=ic, maximomujer__gte=ic)[0]
        else:
            if IndicadorSobrepeso.objects.values('id').filter(minimohombre__lte=ic, maximohombre__gte=ic).exists():
                return IndicadorSobrepeso.objects.filter(minimohombre__lte=ic, maximohombre__gte=ic)[0]
        return None

    def save(self, *args, **kwargs):
        self.inspeccion = self.inspeccion.upper().strip() if self.inspeccion else ''
        self.observaciones = self.observaciones.upper().strip() if self.observaciones else ''
        self.indicecorporal = self.indice_corporal()
        self.indicadorsobrepeso = self.indicador_sobrepeso()
        super(PersonaExamenFisico, self).save(*args, **kwargs)


class Lesiones(ModeloBase):
    tipo = models.CharField(max_length=120, choices=LESIONES_TIPO, verbose_name=u"Tipo")
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Lesione"
        verbose_name_plural = u"Lesiones"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(Lesiones, self).save(*args, **kwargs)


class InspeccionSomatica(ModeloBase):
    personaexamenfisico = models.ForeignKey(PersonaExamenFisico, blank=True, null=True,on_delete=models.CASCADE)
    postura = models.CharField(max_length=20, choices=POSTURA, blank=True, null=True, verbose_name=u"Actitud ó Postura")
    gradoactividad = models.CharField(max_length=20, choices=GRADO_ACTIVIDAD, blank=True, null=True, verbose_name=u"Grado de Actividad")
    estadomental = models.CharField(max_length=20, choices=ESTADO_MENTAL, blank=True, null=True, verbose_name=u"Estado Mental")
    orientaciontiempo = models.BooleanField(blank=True,verbose_name=u'Se orienta en Tiempo y espacio ?')
    colaborainterrogantorio = models.BooleanField(blank=True,verbose_name=u'Colabora con el interrogatorio?')
    estadocaracter = models.CharField(max_length=20, choices=ESTADO_CARACTER, blank=True, null=True, verbose_name=u"Estado Caracter")
    facies = models.CharField(max_length=20, choices=FACIES, blank=True, null=True, verbose_name=u"Facies")
    biotipo = models.CharField(max_length=20, choices=BIOTIPO, blank=True, null=True, verbose_name=u"Biotipo")
    tallaclase = models.CharField(max_length=20, choices=TALLA, blank=True, null=True, verbose_name=u"Talla clase")
    imc = models.FloatField(default=0, verbose_name=u'IMC')
    nutricional = models.CharField(max_length=20, choices=ESTADO_NUTRICIONAL, blank=True, null=True, verbose_name=u"Estado Nutricional")
    color = models.ForeignKey('sga.Raza', verbose_name=u'Color', blank=True, null=True,on_delete=models.CASCADE)
    humedad = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Humedad')
    pilificacion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Pilificación')
    lesioneprimaria = models.ManyToManyField(Lesiones, verbose_name=u'Lesiones Primarias', related_name='Primarias')
    lesionesecundaria = models.ManyToManyField(Lesiones, verbose_name=u'Lesiones Secundarias', related_name='Secundarias')
    pelo = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Pelo')
    unas = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Uñas')
    marcha = models.CharField(max_length=20, choices=TALLA, blank=True, null=True, verbose_name=u"Marcha")
    movimiento = models.CharField(max_length=20, choices=MOVIMIENTO, blank=True, null=True, verbose_name=u"Movimientos")

    def __str__(self):
        return u"%s" % self.personaexamenfisico.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Inspeccion Somatica"
        verbose_name_plural = u"Inspecciones Somaticas"

    def lesione_primaria(self):
        return self.lesioneprimaria.filter(tipo='PRIMARIAS')

    def lesione_secundaria(self):
        return self.lesionesecundaria.all().filter(tipo='SECUNDARIAS')


class InspeccionTopografica(ModeloBase):
    personaexamenfisico = models.ForeignKey(PersonaExamenFisico, blank=True, null=True,on_delete=models.CASCADE)
    craneo = models.CharField(max_length=20, choices=CRANEO, blank=True, null=True, verbose_name=u"Cabeza / Craneo")
    craneotamanio = models.CharField(max_length=20, choices=CRANEO_TAMANIO, blank=True, null=True, verbose_name=u"Tamaño")
    cabelloforma = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Forma')
    cabellocolor = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Color')
    cabelloaspecto = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Aspecto')
    cabellodistribucion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Distribucion')
    cabellocantidad = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Cantidad')
    cabelloconsistencia = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Consistencia')
    cabelloimplantacion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u'Cabello Implantacion')
    caraterciosuperior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cara Tercio Superior')
    caraterciomedio = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cara Tercio Medio')
    caratercioinferior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cara Tercio Inferior')
    cuellocaraanterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cuello Cara Anterior')
    cuellocaralateralderecha = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cuello Cara Lateral Derecha')
    cuellocaralateralizquierda = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cuello Cara Lateral Izquierda')
    cuellocaraposterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Cuello Cara Posterior')
    toraxcaraanterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Torax Cara Anterior')
    toraxcaralateralderecha = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Torax Cara Lateral Derecha')
    toraxcaralateralizquierda = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Torax Cara Lateral Izquierda')
    toraxcaraposterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Torax Cara Posterior')
    abdomenanterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior')
    abdomenanteriorformas = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Formas')
    abdomenanteriorvolumen = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Volúmen')
    abdomenanteriorcicatrizumbilical = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Cicatriz umbilical')
    abdomenanteriorcirculacionlateral = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Circulación Lateral')
    abdomenanteriorcicatrices = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Cicatrices')
    abdomenanteriornebus = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Anterior Nebus')
    abdomenlateralizquierdo = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Lateral Izquierdo')
    abdomenlateralderecho = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Lateral Derecho')
    abdomenposterior = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Abdomen Posterior')
    inguinogenitalvello = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Región Inguinogenital vello')
    inguinogenitalhernias = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Región Inguinogenital Hernias')
    inguinogenitalpene = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Región Inguinogenital Pene')
    superioreshombro = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Superiores Hombro')
    superioresbrazo = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Superiores Brazo')
    superioresantebrazo = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Superiores Antebrazo')
    superioresmano = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Superiores Mano')
    inferiormuslo = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Inferior Muslo')
    inferiorpierna = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Inferior Pierna')
    inferiorpie = models.CharField(max_length=300, blank=True, null=True, verbose_name=u'Inferior Pie')

    def __str__(self):
        return u"%s" % self.personaexamenfisico.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Inspeccion Topografica"
        verbose_name_plural = u"Inspecciones Topograficas"

    def save(self, *args, **kwargs):
        self.cabelloforma = self.cabelloforma.upper().strip() if self.cabelloforma else ''
        self.cabellocolor = self.cabellocolor.upper().strip() if self.cabellocolor else ''
        self.cabelloaspecto = self.cabelloaspecto.upper().strip() if self.cabelloaspecto else ''
        self.cabellodistribucion = self.cabellodistribucion.upper().strip() if self.cabellodistribucion else ''
        self.cabellocantidad = self.cabellocantidad.upper().strip() if self.cabellocantidad else ''
        self.cabelloconsistencia = self.cabelloconsistencia.upper().strip() if self.cabelloconsistencia else ''
        self.cabelloimplantacion = self.cabelloimplantacion.upper().strip() if self.cabelloimplantacion else ''
        self.caraterciosuperior = self.caraterciosuperior.upper().strip() if self.caraterciosuperior else ''
        self.caraterciomedio = self.caraterciomedio.upper().strip() if self.caraterciomedio else ''
        self.caratercioinferior = self.caratercioinferior.upper().strip() if self.caratercioinferior else ''
        self.cuellocaraanterior = self.cuellocaraanterior.upper().strip() if self.cuellocaraanterior else ''
        self.cuellocaralateralderecha = self.cuellocaralateralderecha.upper().strip() if self.cuellocaralateralderecha else ''
        self.cuellocaralateralizquierda = self.cuellocaralateralizquierda.upper().strip() if self.cuellocaralateralizquierda else ''
        self.cuellocaraposterior = self.cuellocaraposterior.upper().strip() if self.cuellocaraposterior else ''
        self.toraxcaraanterior = self.toraxcaraanterior.upper().strip() if self.toraxcaraanterior else ''
        self.toraxcaralateralderecha = self.toraxcaralateralderecha.upper().strip() if self.toraxcaralateralderecha else ''
        self.toraxcaralateralizquierda = self.toraxcaralateralizquierda.upper().strip() if self.toraxcaralateralizquierda else ''
        self.toraxcaraposterior = self.toraxcaraposterior.upper().strip() if self.toraxcaraposterior else ''
        self.abdomenanterior = self.abdomenanterior.upper().strip() if self.abdomenanterior else ''
        self.abdomenanteriorformas = self.abdomenanteriorformas.upper().strip() if self.abdomenanteriorformas else ''
        self.abdomenanteriorvolumen = self.abdomenanteriorvolumen.upper().strip() if self.abdomenanteriorvolumen else ''
        self.abdomenanteriorcicatrizumbilical = self.abdomenanteriorcicatrizumbilical.upper().strip() if self.abdomenanteriorcicatrizumbilical else ''
        self.abdomenanteriorcirculacionlateral = self.abdomenanteriorcirculacionlateral.upper().strip() if self.abdomenanteriorcirculacionlateral else ''
        self.abdomenanteriorcicatrices = self.abdomenanteriorcicatrices.upper().strip() if self.abdomenanteriorcicatrices else ''
        self.abdomenanteriornebus = self.abdomenanteriornebus.upper().strip() if self.abdomenanteriornebus else ''
        self.abdomenlateralizquierdo = self.abdomenlateralizquierdo.upper().strip() if self.abdomenlateralizquierdo else ''
        self.abdomenlateralderecho = self.abdomenlateralderecho.upper().strip() if self.abdomenlateralderecho else ''
        self.abdomenposterior = self.abdomenposterior.upper().strip() if self.abdomenposterior else ''
        self.inguinogenitalvello = self.inguinogenitalvello.upper().strip() if self.inguinogenitalvello else ''
        self.inguindogenitalhernias = self.inguinogenitalhernias.upper().strip() if self.inguinogenitalhernias else ''
        self.inguinogenitalpene = self.inguinogenitalpene.upper().strip() if self.inguinogenitalpene else ''
        self.superioreshombro = self.superioreshombro.upper().strip() if self.superioreshombro else ''
        self.superioresbrazo = self.superioresbrazo.upper().strip() if self.superioresbrazo else ''
        self.superioresantebrazo = self.superioresantebrazo.upper().strip() if self.superioresantebrazo else ''
        self.superioresmano = self.superioresmano.upper().strip() if self.superioresmano else ''
        self.inferiormuslo = self.inferiormuslo.upper().strip() if self.inferiormuslo else ''
        self.inferiorpierna = self.inferiorpierna.upper().strip() if self.inferiorpierna else ''
        self.inferiorpie = self.inferiorpie.upper().strip() if self.inferiorpie else ''
        super(InspeccionTopografica, self).save(*args, **kwargs)


class TipoActividad(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u"Tipo Actividad"
        verbose_name_plural = u"Tipo Actividades"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(TipoActividad, self).save(*args, **kwargs)


class Rutagrama(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    #fechainforme = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha Informe")
    tipovehiculo = models.CharField(max_length=20, choices=TIPO_VEHICULO, blank=True, null=True, verbose_name=u"Tipo Vehiculo")
    destinotrabajo = models.BooleanField(blank=True,verbose_name=u'Destino Trabajo?')
    tiempo = models.CharField(max_length=20, choices=TIEMPO, blank=True, null=True, verbose_name=u"Tiempo")
    horasalida = models.TimeField(verbose_name=u'Hora de Salida', blank=True, null=True)
    tiempoviaja = models.TimeField(verbose_name=u'Tiempo de Viaje', blank=True, null=True)
    escala = models.BooleanField(blank=True,verbose_name=u'Escala?')
    tipoescala = models.CharField(max_length=500, blank=True, null=True, verbose_name=u'Indique Tipo de Escala')
    escala1 = models.TextField(blank=True, null=True, verbose_name=u'Escala Alterna 1')
    escala2 = models.TextField(blank=True, null=True, verbose_name=u'Escala Alterna 2')
    rutaalterna1 = models.TextField(blank=True, null=True, verbose_name=u'Ruta Alterna Posible 1')
    rutaalterna2 = models.TextField(blank=True, null=True, verbose_name=u'Ruta Alterna Posible 2')
    archivo = models.FileField(upload_to='ruta/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo Ruta')
    actividadsalir = models.BooleanField(blank=True,verbose_name=u'Actividades al Salir del Trabajo?')
    tipoactividad = models.ManyToManyField(TipoActividad, verbose_name=u'Tipo de Actividades')
    ubicacion = models.CharField(max_length=20, choices=UBICACION, blank=True, null=True, verbose_name=u"Ubicación")
    tiempoaproximado = models.TimeField(verbose_name=u'Tiempo Aproximado', blank=True, null=True)
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA, blank=True, null=True, verbose_name=u"Frecuencia")
    actividad1 = models.CharField(max_length=600, blank=True, null=True, verbose_name=u'Actividad 1')
    actividad2 = models.CharField(max_length=600, blank=True, null=True, verbose_name=u'Actividad 2')
    actividadcalle = models.TextField(blank=True, null=True, verbose_name=u'Descripcion Breve Actividad en Calle')

    def __str__(self):
        return u"%s" % self.personafichamedica.personaextension.persona.nombre_completo()

    class Meta:
        verbose_name = u"Rutagrama"
        verbose_name_plural = u"Rutagramas"


class RecepcionInsumo(ModeloBase):
    egresobodega = models.ForeignKey("sagest.SalidaProducto", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Comprobante Egreso Bodega")
    fecha = models.DateField(verbose_name=u'Fecha de recepción o ingreso')
    concepto = models.TextField(default='', verbose_name=u'Concepto')
    total = models.FloatField(default=0, verbose_name=u"Total Recibido")
    confirmada = models.BooleanField(default=False, verbose_name=u'Recepción confirmada')

    def __str__(self):
        return u'%s - %s - %s' % (self.id, self.fecha, self.concepto)

    class Meta:
        verbose_name = u"Recepción de Insumos Médicos"
        verbose_name_plural = u"Recepciones de Insumos Médicos"

    def save(self, *args, **kwargs):
        self.concepto = self.concepto.upper()
        super(RecepcionInsumo, self).save(*args, **kwargs)

    def detalles(self):
        # return self.inventariomedicolote_set.filter(status=True).order_by('id')
        return self.recepcioninsumodetalle_set.filter(status=True).order_by('id')

    def puede_editar(self):
        return self.confirmada is False

    def icono_confirmada(self):
        return 'fa fa-check-circle text-success' if self.confirmada else 'fa fa-times-circle text-error'


class RecepcionInsumoDetalle(ModeloBase):
    recepcioninsumo = models.ForeignKey(RecepcionInsumo, on_delete=models.CASCADE, verbose_name=u'Recepción de insumos')
    producto = models.ForeignKey("sagest.Producto", on_delete=models.CASCADE, verbose_name=u"Producto de bodega")
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")
    tipo = models.IntegerField(choices=TIPOINVENTARIOMEDICO_CHOICES, verbose_name=u'Tipo Inventario')
    lote = models.CharField(max_length=100, verbose_name=u"No. Lote")
    fechaelabora = models.DateField(verbose_name=u"Fecha Elaboración")
    fechavence = models.DateField(verbose_name=u"Fecha Vencimiento")
    cantidad = models.FloatField(default=0, verbose_name=u'Cantidad recibida')
    costo = models.FloatField(default=0, verbose_name=u"Costo por unidad")
    costototal = models.FloatField(default=0, verbose_name=u"Costo total")

    def __str__(self):
        return u'%s - %s - %s' % (self.recepcioninsumo,  self.producto.descripcion, self.cantidad)

    class Meta:
        verbose_name = u"Detalle de Recepción de Insumos"
        verbose_name_plural = u"Detalles de Recepción de Insumos"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.lote = self.lote.upper()
        super(RecepcionInsumoDetalle, self).save(*args, **kwargs)


class InventarioMedico(ModeloBase):
    producto = models.ForeignKey("sagest.Producto", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Producto de bodega")
    codigobarra = models.CharField(max_length=50, verbose_name=u'Código barra')
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre del medicamento')
    descripcion = models.CharField(max_length=300, verbose_name=u"Descripción")
    tipo = models.IntegerField(choices=TIPOINVENTARIOMEDICO_CHOICES, verbose_name=u'Tipo Inventario')
    stock = models.FloatField(default=0, verbose_name=u'Stock vigente')

    def __str__(self):
        return "%s - %s (%s)" % (self.codigobarra, self.nombre, self.get_tipo_display())

    class Meta:
        verbose_name = u"Inventario Médico"
        verbose_name_plural = u"Inventarios Médicos"

    def save(self, *args, **kwargs):
        self.codigobarra = self.codigobarra.upper().strip() if self.codigobarra else ''
        self.nombre = self.nombre.upper().strip() if self.nombre else ''
        self.descripcion = self.descripcion.upper().strip() if self.descripcion else ''
        super(InventarioMedico, self).save(*args, **kwargs)

    def flexbox_repr(self):
        return u"%s" % (self.nombre)

    def tipo_rep(self):
        return TIPOINVENTARIOMEDICO_CHOICES[self.tipo - 1][1]

    def existencia(self):
        return null_to_numeric(self.inventariomedicolote_set.aggregate(cantidad=Sum('cantidad'))['cantidad'])


class InventarioMedicoLote(ModeloBase):
    inventariomedico = models.ForeignKey(InventarioMedico, on_delete=models.CASCADE, verbose_name=u"Inventario médico")
    recepcioninsumo = models.ForeignKey(RecepcionInsumo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Recepción de Insumo Médico")
    numero = models.CharField(max_length=100, verbose_name=u"No. Lote")
    fechaelabora = models.DateField(verbose_name=u"Fecha Elaboración")
    fechavence = models.DateField(verbose_name=u"Fecha Vencimiento")
    costo = models.FloatField(default=0, verbose_name=u"Costo por unidad")
    cantidad = models.FloatField(default=0, verbose_name=u'Cantidad recibida')
    stock = models.FloatField(default=0, verbose_name=u'Stock vigente')
    costototal = models.FloatField(default=0, verbose_name=u"Costo total")

    def __str__(self):
        return "%s - %s (%s, LOTE:%s VENCE:%s)" % (self.inventariomedico.codigobarra, self.inventariomedico.nombre, TIPOINVENTARIOMEDICO_CHOICES[self.inventariomedico.tipo - 1][1], self.numero, self.fechavence.strftime("%d-%m-%Y"))

    class Meta:
        verbose_name = u"Inventario Médico - Lote"
        verbose_name_plural = u"Inventarios Médicos - Lotes"
        ordering = ['fechavence', 'inventariomedico__codigobarra']
        unique_together = ('inventariomedico', 'numero',)

    def save(self, *args, **kwargs):
        self.numero = self.numero.upper().strip() if self.numero else ''
        super(InventarioMedicoLote, self).save(*args, **kwargs)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return InventarioMedicoLote.objects.filter(Q(inventariomedico__codigobarra__contains=q) |
                                                   Q(inventariomedico__nombre__contains=q) |
                                                   Q(inventariomedico__descripcion__contains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return self.nombre_inventario_fecha() + " - " + self.id.__str__()

    def nombre_inventario(self):
        return u'%s %s (LOTE: %s, CANT.: %s)' % (self.inventariomedico.codigobarra, self.inventariomedico.nombre, self.numero, self.cantidad)

    def nombre_inventario_fecha(self):
        return u'%s %s (LOTE: %s, CANT.: %s, VENCE: %s)' % (self.inventariomedico.codigobarra, self.inventariomedico.nombre, self.numero, self.cantidad, self.fechavence.strftime("%d-%m-%Y"))

    def movimientos(self):
        return self.inventariomedicomovimiento_set.filter(status=True).order_by('-id')


class InventarioMedicoMovimiento(ModeloBase):
    inventariomedicolote = models.ForeignKey(InventarioMedicoLote,on_delete=models.CASCADE)
    numerodocumento = models.CharField(max_length=100, verbose_name=u'Documento', blank=True, null=True)
    tipo = models.IntegerField(choices=TIPOMOVIMIENTOMEDICAMENTO_CHOICES, default=1, verbose_name=u'Tipo Movimiento')
    fecha = models.DateTimeField(verbose_name=u'Fecha y Hora', blank=True, null=True)
    cantidad = models.FloatField(default=0, verbose_name=u'Cantidad')
    saldoant = models.FloatField(default=0, verbose_name=u'Saldo anterior')
    ingreso = models.FloatField(default=0, verbose_name=u'Cantidad Ingreso')
    salida = models.FloatField(default=0, verbose_name=u'Cantidad salida')
    saldo = models.FloatField(default=0, verbose_name=u'Saldo actual')
    entrega = models.ForeignKey('sga.Persona', verbose_name=u'Entrega', related_name='Entrega', blank=True, null=True,on_delete=models.CASCADE)
    recibe = models.ForeignKey('sga.Persona', verbose_name=u'Recibe', related_name='Recibe', blank=True, null=True,on_delete=models.CASCADE)
    detalle = models.TextField(default='', verbose_name=u'Detalle')
    consultamedica = models.ForeignKey(PersonaConsultaMedica, blank=True, null=True, verbose_name=u'Consulta medica',on_delete=models.CASCADE)
    consultaodontologica = models.ForeignKey(PersonaConsultaOdontologica, blank=True, null=True, verbose_name=u'Consulta odontologica',on_delete=models.CASCADE)
    consultapsicologica = models.ForeignKey(PersonaConsultaPsicologica, blank=True, null=True, verbose_name=u'Consulta psicologica',on_delete=models.CASCADE)

    def __str__(self):
        return "%s - %s" % (self.inventariomedicolote, self.get_tipo_display())

    class Meta:
        verbose_name = u"Inventario Médico - Movimiento"
        verbose_name_plural = u"Inventarios Médicos - Movimientos"

    def save(self, *args, **kwargs):
        self.detalle = self.detalle.upper().strip() if self.detalle else ''
        self.numerodocumento = self.numerodocumento.upper().strip() if self.numerodocumento else ''
        super(InventarioMedicoMovimiento, self).save(*args, **kwargs)


class PersonaFichaNutricion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u"Persona",on_delete=models.CASCADE)
    fechaconsulta = models.DateField(blank=True, null=True, verbose_name=u'Fecha consulta')
    numeroficha = models.IntegerField(blank=True, null=True, verbose_name=u'No. Ficha')
    patologia = models.CharField(blank=True, null=True, max_length=500, verbose_name=u'Patologia')
    antecedentespatologicos = models.CharField(blank=True, null=True, max_length=500, verbose_name=u'Antecedentes patologicos')
    consumoaldia = models.IntegerField(blank=True, null=True, verbose_name=u'Consumo al dia')

    class Meta:
        verbose_name = u"Ficha Nutricion"
        verbose_name_plural = u"Fichas Nutricion"
        unique_together = ('persona',)

    def fichaconsumos(self, consumo):
        lista = False
        if self.consumofichanutricion_set.filter(consumo=consumo,status=True).exists():
            lista = self.consumofichanutricion_set.get(consumo=consumo,status=True)
        return lista

    def save(self, *args, **kwargs):
        super(PersonaFichaNutricion, self).save(*args, **kwargs)


class SintomasAlimentario(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Nombre del sintoma')

    class Meta:
        verbose_name = u"Sintoma Alimentario"
        verbose_name_plural = u"Sintoma Alimentario"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        super(SintomasAlimentario, self).save(*args, **kwargs)


class FrecuenciaConsumo(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Nombre del sintoma')

    class Meta:
        verbose_name = u"Frecuencia Consumo"
        verbose_name_plural = u"Frecuencia Consumo"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        super(FrecuenciaConsumo, self).save(*args, **kwargs)


class Antropometria(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Nombre de la antropometria')
    slug = models.CharField(max_length=250,blank=True, null=True, verbose_name=u'Sobrenombre de antropometria en InBody')

    def __str__(self):
        return f'{self.nombre}'

    def consulta_antropometria(self, consulta):
        return self.consultanutricionantropometria_set.filter(status=True, consulta=consulta).first()

    def en_uso(self):
        return self.consultanutricionantropometria_set.filter(status=True).exists()

    class Meta:
        verbose_name = u"Antropometria"
        verbose_name_plural = u"Antropometria"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        super(Antropometria, self).save(*args, **kwargs)


class Comidas(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Comidas')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Comidas"
        verbose_name_plural = u"Comidass"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        super(Comidas, self).save(*args, **kwargs)


class ConsultaNutricionAntropometria(ModeloBase):
    consulta = models.ForeignKey(PersonaConsultaNutricion, verbose_name=u'Consulta',on_delete=models.CASCADE)
    antropometria = models.ForeignKey(Antropometria, verbose_name=u'Antropometria',on_delete=models.CASCADE)
    valor = models.CharField(null=True, blank=True, max_length=100, verbose_name=u'valor antropometria')
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.consulta}'

class SintomasFichaNutricion(ModeloBase):
    ficha = models.ForeignKey(PersonaFichaNutricion,on_delete=models.CASCADE)
    sintoma = models.ForeignKey(SintomasAlimentario,on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def save(self, *args, **kwargs):
        super(SintomasFichaNutricion, self).save(*args, **kwargs)


class ConsumoFichaNutricion(ModeloBase):
    ficha = models.ForeignKey(PersonaFichaNutricion,on_delete=models.CASCADE)
    consumo = models.ForeignKey(FrecuenciaConsumo,on_delete=models.CASCADE)
    frecuencia = models.IntegerField(choices=FRECUENCIACONSUMO, default=1, verbose_name=u'Frecuencia')
    valor = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        super(ConsumoFichaNutricion, self).save(*args, **kwargs)


class ComidaFichaNutricion(ModeloBase):
    ficha = models.ForeignKey(PersonaFichaNutricion,on_delete=models.CASCADE)
    comida = models.ForeignKey(Comidas,on_delete=models.CASCADE)
    hora = models.TimeField(null=True, blank=True, verbose_name=u"Hora")
    lugar = models.CharField(max_length=500, verbose_name=u'Lugar')
    observacion = models.CharField(max_length=500, verbose_name=u'Observación')

    def save(self, *args, **kwargs):
        super(ComidaFichaNutricion, self).save(*args, **kwargs)


class PruebaLaboratorioFichaNutricion(ModeloBase):
    ficha = models.ForeignKey(PersonaFichaNutricion, verbose_name=u'Ficha nutrición',on_delete=models.CASCADE)
    observacion = models.CharField(max_length=250, verbose_name=u'Prueba')
    valor = models.FloatField(default=0)


class TipoServicioBienestar(ModeloBase):
    descripcion = models.TextField(verbose_name=u"Descripcion")

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Tipo Servicio Bienestar"
        verbose_name_plural = u"Tipo Servicios Bienestars"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoServicioBienestar, self).save(*args, **kwargs)


class RegistrarIngresoBienestar(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona ingreso',on_delete=models.CASCADE)
    regimenlaboral = models.ForeignKey('sagest.RegimenLaboral', blank=True, null=True, verbose_name=u'Regimen Laboral',on_delete=models.CASCADE)
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, verbose_name=u'Inscripción ingreso',on_delete=models.CASCADE)
    tiposerviciobienestar = models.ForeignKey(TipoServicioBienestar, blank=True, null=True, verbose_name=u'Tipo Servicio',on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u"Fecha")
    horainicio = models.TimeField(blank=True, null=True,verbose_name=u'Hora inicio')
    horafin = models.TimeField(blank=True, null=True, verbose_name=u'Hora fin')
    actividad = models.TextField(default='', verbose_name=u"Actividad")

    def __str__(self):
        return u'%s' % self.persona_actual()

    def persona_actual(self):
        if self.persona:
            return self.persona
        else:
            return self.inscripcion.persona

    def numeros(self, fecha):
        if self.inscripcion:
            return RegistrarIngresoBienestar.objects.filter(inscripcion=self.inscripcion, fecha=fecha).count()
        else:
            return RegistrarIngresoBienestar.objects.filter(persona=self.persona, fecha=fecha).count()

    def save(self, *args, **kwargs):
        self.actividad = self.actividad.upper()
        super(RegistrarIngresoBienestar, self).save(*args, **kwargs)

class GrupoAlimento(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u'Nombre de alimento')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Frecuencia Consumo"
        verbose_name_plural = u"Frecuencia Consumo"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        super(GrupoAlimento, self).save(*args, **kwargs)


class BarUniversitario(ModeloBase):
    nombre = models.CharField(max_length=500, verbose_name=u'Nombre')
    responsable = models.CharField(max_length=500, verbose_name=u'Responsable')
    ubicacion = models.CharField(max_length=500, verbose_name=u'Ubicación')

    def __str__(self):
        return u'%s' % self.nombre


class PreguntasBar(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u"Nombre de pregunta")
    activo = models.BooleanField(default=False, verbose_name=u"Activo")
    otros = models.BooleanField(default=False, verbose_name=u"Cuales")

    def __str__(self):
        return u'%s' % self.nombre


class ControlBarUniversitario(ModeloBase):
    baruniversitario = models.ForeignKey(BarUniversitario, verbose_name=u'Bar universitario',on_delete=models.CASCADE)
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    numeroficha = models.IntegerField(blank=True, null=True, verbose_name=u'No. Ficha')
    observaciones = models.TextField(default='', verbose_name=u'Observación')

    def __str__(self):
        return u'%s' % self.baruniversitario


class DatosPsicologico(ModeloBase):
    personafichamedica = models.ForeignKey(PersonaFichaMedica, blank=True, null=True,on_delete=models.CASCADE)
    relemointpadre = models.IntegerField(choices=ALTERNATIVAS, blank=True, null=True, verbose_name=u'Relaciones emocionales interpersonales Padre')
    relemointmadre = models.IntegerField(choices=ALTERNATIVAS, blank=True, null=True, verbose_name=u'Relaciones emocionales interpersonales Madre')
    relemointotros = models.IntegerField(choices=ALTERNATIVAS, blank=True, null=True, verbose_name=u'Relaciones emocionales interpersonales Otros Miembros')

    antecedentes = models.TextField(default='', verbose_name=u"Antecedentes")
    alergia = models.BooleanField(default=False, verbose_name=u'Alergias?')
    nauseas = models.BooleanField(default=False, verbose_name=u'Nauseas?')
    vomito = models.BooleanField(default=False, verbose_name=u'Vómito?')
    anorexia = models.BooleanField(default=False, verbose_name=u'Anorexia?')
    bulimia = models.BooleanField(default=False, verbose_name=u'Bulimia?')
    enuresis = models.BooleanField(default=False, verbose_name=u'Enuresis?')
    encopresis = models.BooleanField(default=False, verbose_name=u'Encopresis?')
    onicofagia = models.BooleanField(default=False, verbose_name=u'Onicofagia?')
    ticsnervioso = models.BooleanField(default=False, verbose_name=u'Tics nervioso?')
    trastornoneurologico = models.BooleanField(default=False, verbose_name=u'Tiene trastornos Neurológicos?')
    edadtrastorno = models.IntegerField(default=0, verbose_name=u'Edad trastornos Neurológicos')
    tratamientotrastorno = models.BooleanField(default=False, verbose_name=u'Tratamiento trastornos Neurológicos?')
    secuelastrastorno = models.BooleanField(default=False, verbose_name=u'Secuelas trastornos Neurológicos?')
    actitudenfermedada = models.TextField(default='', verbose_name=u"Actitud frente a enfermedades")
    actitudmuerte = models.TextField(default='', verbose_name=u"Actitud frente a muerte")
    actitudpadre = models.TextField(default='', verbose_name=u"Actitud frente a padres")

    masturbacionarea = models.BooleanField(default=False, verbose_name=u'Masturbación?')
    curiosidadsexualinfancia = models.BooleanField(default=False, verbose_name=u'Curiosidad Sexual Infancia?')
    edadcuriosidad = models.IntegerField(default=0, verbose_name=u'Edad Curiodidad sexual')
    relaciones = models.TextField(default='', verbose_name=u"Relaciones")
    edaddesarrollosexual = models.IntegerField(default=0, verbose_name=u'Edad desarrollo sexual')
    actitudpadredesarrollosexual = models.TextField(default='', verbose_name=u"Actitud de padres frente al desarrollo sexual")

    amigospreferidos = models.BooleanField(default=False, verbose_name=u'Amigos(as) preferidos?')
    numeroamigos = models.IntegerField(default=0, verbose_name=u'Numero de Amigos')
    comportamientoanteadulto = models.IntegerField(choices=ALTERNATIVASVARIAS, blank=True, null=True, verbose_name=u'Relaciones emocionales interpersonales Padre')
    relacompaneros = models.IntegerField(choices=ALTERNATIVAS, blank=True, null=True, verbose_name=u'Relaciones con compañeros')
    relamaestros = models.IntegerField(choices=ALTERNATIVAS, blank=True, null=True, verbose_name=u'Relaciones con maestros')

    dificultadcaminar = models.BooleanField(default=False, verbose_name=u'Dificultad al caminar?')
    lenguaje = models.IntegerField(default=0, verbose_name=u'Lenguaje(Edad)')
    balbuceo = models.BooleanField(default=False, verbose_name=u'Balbuceo?')
    imitasonido = models.BooleanField(default=False, verbose_name=u'Imitación de sonidos?')
    silabas = models.BooleanField(default=False, verbose_name=u'Silabas?')
    primerapalabra = models.BooleanField(default=False, verbose_name=u'Primera palabras?')
    frases = models.BooleanField(default=False, verbose_name=u'Frases?')
    dificultades = models.BooleanField(default=False, verbose_name=u'Frases?')
    idiomas = models.ManyToManyField('sga.Idioma')
    estadoactual = models.TextField(default='', verbose_name=u"Estado Actual")

    separacionmatrimonial = models.BooleanField(default=False, verbose_name=u'Separaciones matrimoniales?')
    cambioresidencia = models.BooleanField(default=False, verbose_name=u'Cambios de residencia?')
    enfermedades = models.BooleanField(default=False, verbose_name=u'Enfermedades?')
    defunciones = models.BooleanField(default=False, verbose_name=u'Defunciones?')
    viajesprolongados = models.BooleanField(default=False, verbose_name=u'Viajes Prolongados?')
    problemaeconomicos = models.BooleanField(default=False, verbose_name=u'Problemas Económicos?')

    edadprimerarelacion = models.IntegerField(default=0, verbose_name=u'Edad primera relación sexual')
    matrimoniounion = models.BooleanField(default=False, verbose_name=u'Matrimonio/Unión?')
    compromisosociales = models.BooleanField(default=False, verbose_name=u'Compromiso Sociales?')
    cargotrabajo = models.TextField(default='', verbose_name=u"Cargo de Trabajo")
    masturbacionadolecencia = models.BooleanField(default=False, verbose_name=u'Masturbación Adolecencia?')
    alcoholadolecencia = models.BooleanField(default=False, verbose_name=u'Alcohol Adolecencia?')
    edadalcohol = models.IntegerField(default=0, verbose_name=u'Edad alcohol adolecencia')
    motivoalcohol = models.TextField(default='', verbose_name=u"Motivo por ingerir alcohol")
    drogasadolecencia = models.BooleanField(default=False, verbose_name=u'Drogas Adolecencia?')
    edaddrogas = models.IntegerField(default=0, verbose_name=u'Edad drogas adolecencia')
    motivodrogas = models.TextField(default='', verbose_name=u"Motivo por ingerir drogas")

    enamoramiento = models.BooleanField(default=False, verbose_name=u'Enamoramiento?')
    cantidadrelaciones = models.IntegerField(default=0, verbose_name=u'Cantidad de relaciones')
    ultimarelacion = models.IntegerField(default=0, verbose_name=u'Tiempo de ultima Relación')
    matrimoniounionadulto = models.BooleanField(default=False, verbose_name=u'Matrimonio/Unión?')
    edadultimarelacion = models.IntegerField(default=0, verbose_name=u'Edad de ultima Relación')
    masturbacionadulto = models.BooleanField(default=False, verbose_name=u'Masturbación Adolecencia?')
    compromisosocialesadulto = models.BooleanField(default=False, verbose_name=u'Compromiso Sociales?')
    cargotrabajoadulto = models.TextField(default='', verbose_name=u"Cargo de Trabajo")
    alcoholadolecenciaadulto = models.BooleanField(default=False, verbose_name=u'Alcohol Adolecencia?')
    edadalcoholadulto = models.IntegerField(default=0, verbose_name=u'Edad alcohol adolecencia')
    motivoalcoholadulto = models.TextField(default='', verbose_name=u"Motivo por ingerir alcohol")
    drogasadolecenciaadulto = models.BooleanField(default=False, verbose_name=u'Drogas Adolecencia?')
    edaddrogasadulto = models.IntegerField(default=0, verbose_name=u'Edad drogas adolecencia')
    motivodrogasadulto = models.TextField(default='', verbose_name=u"Motivo por ingerir drogas")

    def __str__(self):
        return u"%s" % self.personafichamedica

    class Meta:
        verbose_name = u"Dato Psicologico"
        verbose_name_plural = u"Datos Psicologicos"

    def idiomasall(self):
        return self.idiomas.all()

    def save(self, *args, **kwargs):
        super(DatosPsicologico, self).save(*args, **kwargs)


class ConservacionControlBarUniversitario(ModeloBase):
    control = models.ForeignKey(ControlBarUniversitario, verbose_name=u'Control bar universitario',on_delete=models.CASCADE)
    conservacion = models.ForeignKey(GrupoAlimento, verbose_name=u'Conservacion alimentos',on_delete=models.CASCADE)
    tipoconservacion = models.IntegerField(choices=TIPO_CONSERVACION, default=1, verbose_name=u'Tipo Movimiento')

    def __str__(self):
        return u'%s' % self.control


class RespuestaControlBarUniversitario(ModeloBase):
    control = models.ForeignKey(ControlBarUniversitario, verbose_name=u'Control bar universitario',on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PreguntasBar, verbose_name=u'Preguntas',on_delete=models.CASCADE)
    valor = models.IntegerField(blank=True, null=True, verbose_name=u'Valor respuesta')
    observacion = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Cuales')

    def __str__(self):
        return u'%s' % self.control


class TemasPlanificacion(ModeloBase):
    tema = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Tema')
    objetivo = models.TextField(verbose_name=u'Objetivo', blank=True, null=True)
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, verbose_name=u'Periodo',on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.tema

    def en_uso(self):
        if self.cursotemasplanificacion_set.filter(status=True).exists():
            return True
        else:
            return False


class CursoTemasPlanificacion(ModeloBase):
    tema = models.ForeignKey(TemasPlanificacion, verbose_name=u'Tema',on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', blank=True, null=True, verbose_name=u'Carrera',on_delete=models.CASCADE)
    nivelmalla = models.ForeignKey('sga.NivelMalla', blank=True, null=True, verbose_name=u'Nivel malla',on_delete=models.CASCADE)
    paralelo = models.ForeignKey('sga.Paralelo', blank=True, null=True, verbose_name=u'Paralelo',on_delete=models.CASCADE)
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    nivel = models.ForeignKey('sga.Nivel', blank=True, null=True, verbose_name=u'Nivel',on_delete=models.CASCADE)
    coordinacion = models.ForeignKey('sga.Coordinacion', blank=True, null=True, verbose_name=u'Coordinacion',on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.tema

    def total_participantes(self):
        return self.participantescursotemasplanificacion_set.filter(status=True).count()

    def total_asistencias(self):
        return self.participantescursotemasplanificacion_set.filter(asistencia=True).count()

    def total_faltas(self):
        return self.participantescursotemasplanificacion_set.filter(asistencia=False).count()


class ParticipantesCursoTemasPlanificacion(ModeloBase):
    curso = models.ForeignKey(CursoTemasPlanificacion, verbose_name=u'curso',on_delete=models.CASCADE)
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Matricula',on_delete=models.CASCADE)
    asistencia = models.BooleanField(default=False, verbose_name=u'Activo')
    inscripcionmanual = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.tema


class PsicologicoPreguntasBancoEscala(ModeloBase):
    descripcion = models.TextField(verbose_name=u'Escala')
    leyenda = models.TextField(blank=True, null=True, verbose_name=u"Leyenda")

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Escala de Pregunta Psicológica"
        verbose_name_plural = u"Escalas de Preguntas Psicológicas"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip()
        self.leyenda = self.leyenda.strip()
        super(PsicologicoPreguntasBancoEscala, self).save(*args, **kwargs)

    def can_delete(self):
        return not TestPsicologicoPreguntas.objects.filter(escala=self).exists()


class PsicologicoPreguntasBanco(ModeloBase):
    descripcion = models.TextField(verbose_name=u'Pregunta')
    leyenda = models.TextField(blank=True, null=True, verbose_name=u"Leyenda")

    def __str__(self):
        return u'%s' % self.descripcion

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return PsicologicoPreguntasBanco.objects.filter(Q(nombre__contains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u"%s (%s)" % (self.descripcion, self.leyenda)

    def flexbox_alias(self):
        return [self.descripcion, self.leyenda]

    class Meta:
        verbose_name = u"Pregunta Psicológica"
        verbose_name_plural = u"Preguntas Psicológicas"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip()
        self.leyenda = self.leyenda.strip()
        super(PsicologicoPreguntasBanco, self).save(*args, **kwargs)

    def can_delete(self):
        return not TestPsicologicoPreguntas.objects.filter(pregunta=self).exists()


class TestPsicologico(ModeloBase):
    nombre = models.CharField(max_length=500, verbose_name=u'Titulo del test')
    subnombre = models.CharField(max_length=500, verbose_name=u'Subtitulo del test', blank=True, null=True)
    instruccion = models.TextField(blank=True, null=True, verbose_name=u"Instrucción")
    version = models.IntegerField(default=1, blank=True, null=True, verbose_name=u'Versión del test')

    def __str__(self):
        return u'%s (V%s)' % (self.nombre, self.version)

    class Meta:
        verbose_name = u"Test Psicológico"
        verbose_name_plural = u"Test Psicológicos"
        unique_together = ('nombre', 'version',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        self.subnombre = self.subnombre.upper().strip()
        super(TestPsicologico, self).save(*args, **kwargs)

    def can_delete(self):
        return not PersonaTestPsicologica.objects.filter(test=self).exists()


class TestPsicologicoPreguntas(ModeloBase):
    test = models.ForeignKey(TestPsicologico, verbose_name=u"Test", related_name='+',on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PsicologicoPreguntasBanco, verbose_name=u"Pregunta", related_name='+',on_delete=models.CASCADE)
    escala = models.ForeignKey(PsicologicoPreguntasBancoEscala, related_name='+', blank=True, null=True, verbose_name=u"Escala",on_delete=models.CASCADE)
    tiporespuesta = models.ForeignKey('sga.TipoRespuesta', blank=True, null=True, verbose_name=u"Tipo de Respuesta",on_delete=models.CASCADE)
    orden = models.IntegerField(default=1, blank=True, null=True, verbose_name=u'Orden de la Pregunta')

    def __str__(self):
        if self.escala and self.orden:
            return u'%s - %s - Pregunta Nro.%s' % (self.test, self.escala, self.orden)
        elif self.escala or self.orden:
            if self.escala:
                return u'%s - %s' % (self.test, self.escala)
            else:
                return u'%s - Pregunta Nro.%s' % (self.test, self.orden)
        else:
            return u'%s - Pregunta: %s' % (self.test, self.pregunta)

    class Meta:
        verbose_name = u"Pregunta del Test Psicológico"
        verbose_name_plural = u"Preguntas del Test Psicológico"

    def save(self, *args, **kwargs):
        super(TestPsicologicoPreguntas, self).save(*args, **kwargs)


class RespuestaTestPsicologica(ModeloBase):
    pregunta = models.ForeignKey(PsicologicoPreguntasBanco, verbose_name=u"Pregunta", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    respuesta = models.ForeignKey('sga.Respuesta', verbose_name=u"Respuesta", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    respuesta_valor = models.FloatField(default=0, null=True, blank=True, verbose_name=u'Valor de la respuesta')
    respuesta_children = models.ForeignKey('sga.Respuesta', verbose_name=u"Respuesta Children", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    respuesta_children_valor = models.FloatField(default=0, null=True, blank=True, verbose_name=u'Valor de la respuesta hija')

    def __str__(self):
        return u'%s' % self.pregunta

    class Meta:
        verbose_name = u"Respuesta - Test Psicológico"
        verbose_name_plural = u"Respuestas - Test Psicológicos"

    def save(self, *args, **kwargs):
        super(RespuestaTestPsicologica, self).save(*args, **kwargs)


class PersonaTestPsicologica(ModeloBase):
    from django.contrib.auth.models import Group
    persona = models.ForeignKey('sga.persona', verbose_name=u"Persona", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    test = models.ForeignKey(TestPsicologico, verbose_name=u"Test Psicológico", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u"Fecha de aplicación")
    respuestas = models.ManyToManyField(RespuestaTestPsicologica)
    medico = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Medico',on_delete=models.CASCADE)
    diagnostico = models.TextField(verbose_name=u'Diagnostico Medico', blank=True, null=True)
    diagnosticoverbose = models.TextField(verbose_name=u'Diagnostico Cliente', blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.persona, self.test)

    class Meta:
        verbose_name = u"Persona - Test Psicológico"
        verbose_name_plural = u"Personas - Test Psicológicos"

    def save(self, *args, **kwargs):
        super(PersonaTestPsicologica, self).save(*args, **kwargs)


class TestPsicologicoCalculoDiagnostico(ModeloBase):
    test = models.ForeignKey(TestPsicologico, verbose_name=u"Test Psicológico", blank=True, null=True, related_name='+',on_delete=models.CASCADE)
    nombreaccion = models.CharField(max_length=500, verbose_name=u'Titulo del test')

    def __str__(self):
        return u'%s (%s)' % (self.test, self.nombreaccion)

    class Meta:
        verbose_name = u"Test Psicológico calculo diagnostico"
        verbose_name_plural = u"Test Psicológicos calculos diagnostico"
        unique_together = ('nombreaccion', 'test',)

    def save(self, *args, **kwargs):
        self.nombreaccion = self.nombreaccion.lower().strip()
        super(TestPsicologicoCalculoDiagnostico, self).save(*args, **kwargs)
