from datetime import timedelta, datetime

from django.db import models
# Create your models here.
from django.db.models import Q

from balcon.models import EncuestaProceso, RespuestaEncuestaSatisfaccion
from sga.funciones import remover_caracteres_especiales_unicode, ModeloBase
from sga.models import PerfilUsuario, DIAS_CHOICES, TIPOS_PERFILES, Carrera, ParentescoPersona


class TurnoPolideportivo(ModeloBase):
    turno = models.IntegerField(default=0, verbose_name=u'Turno')
    comienza = models.TimeField(verbose_name=u'Comienza')
    termina = models.TimeField(verbose_name=u'Termina')
    # horas = models.FloatField(default=0, verbose_name=u'Horas')
    mostrar = models.BooleanField(default=True, verbose_name=u"Mostrar")

    def __str__(self):
        return u'Comienza: %s - Termina: %s' % (self.comienza, self.termina)

    def nombre_horario(self):
        return self.comienza.strftime("%H:%M") + ' a ' + self.termina.strftime("%H:%M")

    def fechas_horarios(self):
        return self.comienza.strftime('%d-%m-%Y') + " a " + self.fechafin.strftime('%d-%m-%Y')

    def puede_eliminar(self):
        if self.horarioactividadpolideportivo_set.filter(status=True).exists():
            return False
        return True

    class Meta:
        verbose_name = u"Turno polideportivo"
        verbose_name_plural = u"Turnos polideportivo"
        unique_together = ('comienza', 'termina',)


class SancionPolideportivo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    valor = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor')
    mostrar = models.BooleanField(default=False, verbose_name=u'mostrar')

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(SancionPolideportivo, self).save(*args, **kwargs)


ESTADO_RESERVA_POLIDEPORTIVO = ((1, u'Pendiente'), (2, u'Reservado'), (3, u'Anulado'), (4, u'Finalizado'),)

TIPO_TERCERO = (
    (1, u'Familiar'),
    (2, u'Externos'),
    (3, u'Grupal'),
)

TIPO_ACTIVIDAD = (
    (1, u'General'),
    (2, u'Escuela formativa'),
    (3, u'Vacacional')
)

class AreaPolideportivo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    numdias = models.IntegerField(default=0, verbose_name='Número de días para reservación')
    portada = models.FileField(upload_to='areapolideportivo', blank=True, null=True, verbose_name=u'Portada del Área')
    fondo = models.FileField(upload_to='areapolideportivo/fondo', blank=True, null=True, verbose_name=u'Fondo del Área')
    en_mantenimiento = models.BooleanField(default=False, verbose_name=u'¿En Mantenimiento?')

    def get_portada(self):
        if self.portada:
            return f'https://sga.unemi.edu.ec/{self.portada.url}'
        else:
            return f'/static/images/polideportivo/escuelasformativas.png'

    def get_fondo(self):
        if self.fondo:
            return f'https://sga.unemi.edu.ec/{self.fondo.url}'
        else:
            return f'/static/images/polideportivo/escuelasformativas.png'

    def total_fotos(self):
        qsfotos = self.fotosareapolideportivo_set.filter(status=True)
        totactivos = qsfotos.filter(visible=True).count()
        totinactivos = qsfotos.filter(visible=False).count()
        totfotos = qsfotos.count()
        return {'totfotos': totfotos, 'totvisibles': totactivos, 'totnovisibles': totinactivos}

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def en_mantenimiento_str(self):
        return 'fa fa-check-circle text-success' if self.en_mantenimiento else 'fa fa-times-circle text-error'

    def secciones(self):
        return self.seccionpolideportivo_set.filter(status=True)

    def cantidad_cupo_secciones(self, turno, lista, fecha):
        cantidad = 0
        secciones = self.seccionpolideportivo_set.filter(status=True, id__in=lista)
        for seccion in secciones:
            cantidad += seccion.cupo_disponible_seccion(fecha, turno)
        return cantidad

    def listado_cupos(self, turno, lista, fecha):
        list = []
        secciones = self.seccionpolideportivo_set.filter(status=True, id__in=lista)
        for seccion in secciones:
            cupos = seccion.cupo_disponible_seccion(fecha, turno)
            diccionario = {'id': seccion.id, 'cupos': cupos}
            list.append(diccionario)
        ordenados = sorted(list, key=lambda l: l['cupos'])
        # list.clear()
        # for orden in ordenados:
        #     list.append(orden.get('id'))
        return ordenados

    def puede_eliminar(self):
        if self.actividadpolideportivo_set.filter(status=True).exists():
            return False
        return True

    def actividades(self):
        return self.actividadpolideportivo_set.filter(status=True)

    def actividades_limitadas(self, perfilprincipal, perfil=None):
        lista = []
        # perfil = None
        # carrera = None
        actividades = self.actividadpolideportivo_set.filter(mostrar=True, status=True).order_by('nombre')
        if not perfil:
            if perfilprincipal.es_estudiante() or perfilprincipal.es_inscripcionaspirante():
                perfil = 1
                carrera = perfilprincipal.inscripcion.carrera
                actividades = actividades.filter(Q(carreras=carrera) | Q(carreras=None))
            elif perfilprincipal.es_administrativo():
                perfil = 2
            elif perfilprincipal.es_profesor():
                perfil = 3
            elif perfilprincipal.es_externo():
                perfil = 4
        for actividad in actividades:
            perfiles = PerfilesActividad.objects.filter(status=True, actividad=actividad)
            if perfiles.filter(perfil=perfil, activo=True).exists():
                lista.append(actividad)
        diccionario = {'lista': lista[:5], 'cantidad': len(lista)}
        return diccionario

    def __str__(self):
        return u'%s' % (self.nombre)

    # def save(self, *args, **kwargs):
    #     self.nombre = self.nombre.upper().strip()
    #     super(AreaPolideportivo, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Área Polideportivos"
        verbose_name_plural = u"Áreas Polideportivos"


class FotosAreaPolideportivo(ModeloBase):
    area = models.ForeignKey(AreaPolideportivo, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Área')
    orden = models.IntegerField(default=0, verbose_name='Orden')
    foto = models.FileField(upload_to='fotoareaspoli', blank=True, null=True, verbose_name=u'Foto')
    visible = models.BooleanField(default=False, verbose_name=u'¿Visible?')

    def visible_str(self):
        return 'fa fa-check-circle text-success' if self.visible else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s %s' % (self.orden, self.area.nombre)

    class Meta:
        verbose_name = u"Fotos Área Polideportivos"
        verbose_name_plural = u"Fotos Áreas Polideportivos"


class SeccionPolideportivo(ModeloBase):
    area = models.ForeignKey(AreaPolideportivo, on_delete=models.PROTECT, verbose_name='Área')
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    mostrar = models.BooleanField(default=False, verbose_name=u'mostrar')
    cupo = models.IntegerField(default=0, verbose_name=u"Cantidad máxima de personas por seccion")
    fondo = models.FileField(upload_to='seccionpolideportivo', blank=True, null=True, verbose_name=u'fondo de sección')
    icono = models.FileField(upload_to='seccionpolideportivo', blank=True, null=True, verbose_name=u'ícono de sección')

    def __str__(self):
        return u'%s %s' % (self.nombre, self.area)

    def subsecciones(self):
        return self.subseccionpolideportivo_set.filter(status=True)

    def cupo_disponible_seccion(self, fecha, turno):
        try:
            cantidad = 0
            reservaciones = self.reservacionturnospoli_set.filter(status=True, turno=turno, fechareservacion__reservacion__finicialreserva=fecha)
            for reservacion in reservaciones:
                cantiadseccion = 0
                # familiares = len(ReservacionTercerosPoli.objects.filter(status=True, reservacion=reservacion.fechareservacion.reservacion))
                if reservacion.reservacionseccionpoli_set.filter(status=True, seccion=self).exists():
                    seccion = reservacion.reservacionseccionpoli_set.get(status=True, seccion=self)
                    cantiadseccion = seccion.cantidad
                cantidad += cantiadseccion
            cantidad = self.cupo - cantidad
            return cantidad
        except Exception as ex:
            pass

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    class Meta:
        verbose_name = u"Sección Polideportivo"
        verbose_name_plural = u"Secciones Polideportivo"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(SeccionPolideportivo, self).save(*args, **kwargs)


class ActividadPolideportivo(ModeloBase):
    area = models.ForeignKey(AreaPolideportivo, on_delete=models.PROTECT, verbose_name='Área')
    disciplina = models.ForeignKey('sga.DisciplinaDeportiva', blank=True, null=True, on_delete=models.PROTECT, verbose_name='Disciplina')
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')
    cupo = models.IntegerField(default=0, verbose_name=u"Cantidad máxima de personas por turno")
    interno = models.BooleanField(default=False, verbose_name=u'Interno')
    externo = models.BooleanField(default=False, verbose_name=u'Externo')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    responsable = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona responsable', on_delete=models.CASCADE)
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    portada = models.FileField(upload_to='actividadpolideportivo', blank=True, null=True, verbose_name=u'Portada de la actividad')
    valor = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor')
    carreras = models.ManyToManyField(Carrera, verbose_name=u'Carreras')
    numacompanantes = models.IntegerField(default=10, verbose_name='Número de acompañantes permitidos')
    tipoactividad = models.IntegerField(default=1, choices=TIPO_ACTIVIDAD, verbose_name='Tipo de actividad')

    def __str__(self):
        return u'%s' % (self.nombre)

    def name_estadistica(self):
        return f'{self.nombre}'

    def instructores(self):
        return self.instructoractividadpolideportivo_set.filter(status=True)

    def horarios_activos(self, dia, turno, planificacion=None):
        horarios = self.horarioactividadpolideportivo_set.filter(dia=dia, turno=turno, status=True, planificacion=planificacion)
        return horarios.order_by('turno__turno')

    def horarios_disponibles_dia(self, dia, turno, planificacion=None):
        horarios = self.horarios_activos(dia, turno, planificacion).filter(mostrar=True)
        ids_excluir = []
        for horario in horarios:
            if horario.cupos_disponible_planificacion() <= 0:
                ids_excluir.append(horario.id)
        return horarios.exclude(id__in=ids_excluir).order_by('turno__comienza', 'turno__termina')

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.nombre).lower().replace(' ', '_')

    def tiene_horarios(self):
        if self.horarioactividadpolideportivo_set.values_list('id').filter(status=True).exists():
            return 'Configurado'
        return 'No registra'

    def horario_disponible(self):
        return self.horarioactividadpolideportivo_set.values_list('id').filter(status=True).exists()

    def implementos(self):
        return self.implementosactividad_set.filter(status=True)

    def puede_eliminar(self):
        if self.horarioactividadpolideportivo_set.filter(status=True).exists():
            return False
        elif self.implementosactividad_set.filter(status=True).exists():
            return False
        elif self.instructoractividadpolideportivo_set.filter(status=True).exists():
            return False
        elif self.reservacionpersonapoli_set.filter(status=True).exists():
            return False
        return True

    def encuesta(self):
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self)
        return EncuestaProceso.objects.filter(object_id=self.id, content_type=content_type, status=True, vigente=True).first()

    def encuesta_configurada(self):
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self)
        return EncuestaProceso.objects.filter(object_id=self.id, content_type=content_type, status=True).first()

    def tiene_preguntas(self):
        return self.encuesta().preguntas_obj() if self.encuesta() else None

    def preguntas_encuesta(self):
        return self.encuesta_configurada().preguntas_para_estadisticas() if self.encuesta_configurada() else None

    def get_portada(self):
        if self.portada:
            return f'{self.portada.url}'
        else:
            return f''

    def reservas(self):
        return self.reservacionpersonapoli_set.filter(status=True)

    def cupos_disponibles(self):
        return self.cupo - len(self.reservas().exclude(estado=3))

    def len_planificaciones(self):
        return len(self.planificacionactividad_set.filter(status=True))

    def get_planificacion(self):
        return self.planificacionactividad_set.filter(status=True, activo=True )

    class Meta:
        verbose_name = u"Actividad polideportivo"
        verbose_name_plural = u"Actividades Polideportivo"

    # def save(self, *args, **kwargs):
    #     self.nombre = self.nombre.upper().strip()
    #     super(ActividadPolideportivo, self).save(*args, **kwargs)

class PlanificacionActividad(ModeloBase):
    actividad = models.ForeignKey(ActividadPolideportivo, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Actividad')
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    costo = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Costo')
    activo = models.BooleanField(default=False, verbose_name=u'activo')
    cupo = models.IntegerField(default=0, verbose_name=u"Cantidad de cupos disponibles")

    def __str__(self):
        return f'{self.nombre}'

    def generar_turno(self, persona):
        num = str(len(ReservacionPersonaPoli.objects.all()) + 1)
        if len(num) == 1:
            num = '000' + num
        elif len(num) == 2:
            num = '00' + num
        elif len(num) == 3:
            num = '0' + num
        actividad = (self.actividad.nombre[0:3]).upper()
        arreglo = persona.split()
        siglas = ''
        for letra in arreglo:
            siglas += letra[:1]
        return str(siglas + '-' + actividad + '-' + num)

    def desactivar_planificaciones(self):
        planificaciones = PlanificacionActividad.objects.filter(actividad=self.actividad, status=True, activo=True)
        planificaciones.update(activo=False)

    def reservas(self):
        return self.reservacionpersonapoli_set.filter(status=True)

    def tiene_reserva(self, persona, idfamiliar=None):
        filtro = Q(status=True, persona=persona)
        if not idfamiliar:
            filtro = filtro & Q(tercero=False)
        else:
            filtro = filtro & Q(familiar_id=idfamiliar, tercero=True)
        return self.reservacionpersonapoli_set.filter(filtro).exists()

    def cupos_disponibles(self):
        return self.cupo - len(self.reservas().exclude(estado=3))

    def horarios_disponibles(self):
        horarios = self.horarioactividadpolideportivo_set.filter(status=True, mostrar=True)
        ids_excluir = []
        for horario in horarios:
            if horario.cupos_disponible_planificacion() <= 0:
                ids_excluir.append(horario.id)
        return horarios.exclude(id__in=ids_excluir).order_by('turno__comienza', 'turno__termina')

    def tope_dias(self):
        ultimo_dia=self.horarios_disponibles().order_by('dia').values_list('dia', flat=True).distinct().last()
        return ultimo_dia if ultimo_dia else 0


    def turnos_disponibles(self):
        turnos = self.horarios_disponibles().values_list('turno_id', flat=True).order_by('turno_id').distinct()
        return TurnoPolideportivo.objects.filter(id__in=turnos).order_by('comienza', 'termina')

    class Meta:
        verbose_name = u"Planificación de Actividad polideportivo"
        verbose_name_plural = u"Planificaciones de Actividades Polideportivo"
        ordering =('-fechainicio',)

class PoliticaPolideportivo(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    mostrar = models.BooleanField(default=False, verbose_name=u'mostrar')
    general = models.BooleanField(default=False, verbose_name=u'politica general')
    area = models.ManyToManyField(AreaPolideportivo, verbose_name=u'Àreas')

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(PoliticaPolideportivo, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Política de polideportivo"
        verbose_name_plural = u"Políticas de Polideportivo"


class PerfilesActividad(ModeloBase):
    actividad = models.ForeignKey(ActividadPolideportivo, on_delete=models.PROTECT, blank=True, null=True, verbose_name='actividad')
    perfil = models.IntegerField(choices=TIPOS_PERFILES, blank=True, null=True, verbose_name=u'Perfil')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')
    familiares = models.ManyToManyField(ParentescoPersona, verbose_name='Familiares disponibles para el perfil')

    def __str__(self):
        return "{} - {}".format(self.get_perfil_display(), self.actividad.nombre)

    def descuentos(self):
        return self.descuentovaloractividad_set.filter(status=True)


class ImplementosActividad(ModeloBase):
    actividad = models.ForeignKey(ActividadPolideportivo, on_delete=models.PROTECT, blank=True, null=True, verbose_name='actividad')
    utensilio = models.ForeignKey('sga.Utensilios', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Utinsilios')
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad de implementos")
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return "{} - {}".format(self.utensilio, self.cantidad)

    class Meta:
        verbose_name = u"Utensilio de reservación"
        verbose_name_plural = u"Utensilios de reservación"


class InstructorPolideportivo(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Instructor', on_delete=models.CASCADE)
    activo = models.BooleanField(default=False, verbose_name=u'Activo')
    descripcion = models.CharField(default='', max_length=5000, verbose_name=u'Descripción')

    def __str__(self):
        return u'%s' % (self.persona)

    def get_activo(self):
        return 'fa fa-check-circle text-success' if self.activo else 'fa fa-times-circle text-error'

    def actividades(self):
        return self.instructoractividadpolideportivo_set.filter(status=True)

    def disciplinas(self):
        return self.instructoractividadpolideportivo_set.filter(status=True).values_list('actividad__disciplina__descripcion', flat=True).order_by('actividad__disciplina__descripcion').distinct()

    class Meta:
        verbose_name = u"Instructor de polideportivo"
        verbose_name_plural = u"Instructores de polideportivo"


class InstructorActividadPolideportivo(ModeloBase):
    actividad = models.ForeignKey(ActividadPolideportivo, on_delete=models.PROTECT, verbose_name='Actividad')
    instructor = models.ForeignKey(InstructorPolideportivo, on_delete=models.PROTECT, verbose_name='Instructor')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s %s' % (self.instructor, self.actividad)

    def puede_eliminar(self):
        if HorarioActividadPolideportivo.objects.filter(status=True).exists():
            return False
        return True

    class Meta:
        verbose_name = u"Instructor de actividad"
        verbose_name_plural = u"Instructores de actividad"


class HorarioActividadPolideportivo(ModeloBase):
    instructor = models.ForeignKey(InstructorActividadPolideportivo, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Instructor')
    turno = models.ForeignKey(TurnoPolideportivo, on_delete=models.PROTECT, verbose_name='Turno')
    actividad = models.ForeignKey(ActividadPolideportivo, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Actividad')
    planificacion = models.ForeignKey(PlanificacionActividad, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Planificación de actividad')
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicial')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')

    # secciones = models.ManyToManyField(SeccionPolideportivo, verbose_name=u'Secciones')

    def __str__(self):
        return u'%s %s' % (self.actividad, self.turno)

    def generar_turno(self, persona):
        num = str(len(ReservacionPersonaPoli.objects.all()) + 1)
        if len(num) == 1:
            num = '000' + num
        elif len(num) == 2:
            num = '00' + num
        elif len(num) == 3:
            num = '0' + num
        actividad = (self.actividad.nombre[0:3]).upper()
        arreglo = persona.split()
        siglas = ''
        for letra in arreglo:
            siglas += letra[:1]
        return str(siglas + '-' + actividad + '-' + num)

    def cupos_reservados(self, fecha):
        try:
            cantidad = 0
            reservas = ReservacionTurnosPoli.objects.filter(turno=self, status=True,
                                                            fechareservacion__reservacion__finicialreserva=fecha,
                                                            fechareservacion__reservacion__estado__in=[1, 2])
            cantidad = len(reservas)
            for reserva in reservas:
                if reserva.fechareservacion.reservacion.tipotercero == 2:
                    cantidad += reserva.fechareservacion.reservacion.cantidad
                elif reserva.fechareservacion.reservacion.tipotercero == 1 or reserva.fechareservacion.reservacion.tipotercero == 3:
                    cantidad += len(reserva.reservaciontercerospoli_set.filter(status=True))
            turnos = self.actividad.cupo - cantidad
            return turnos
        except Exception as ex:
            pass

    def cupos_disponibles(self):
        reservas = ReservacionTurnosPoli.objects.filter(turno=self, status=True,
                                                        fechareservacion__reservacion__estado__in=[1, 2, 4])
        cantidad = len(reservas)
        for reserva in reservas:
            if reserva.fechareservacion.reservacion.tipotercero == 2:
                cantidad += reserva.fechareservacion.reservacion.cantidad
            elif reserva.fechareservacion.reservacion.tipotercero == 3:
                cantidad += len(reserva.reservaciontercerospoli_set.filter(status=True))
        cantidad = self.actividad.cupo - cantidad
        return cantidad

    def cupos_disponible_fecha(self, fecha):
        reservas = self.reservacionturnospoli_set.filter(status=True,
                                                        fechareservacion__freservacion=fecha,
                                                        fechareservacion__reservacion__estado__in=[1, 2, 4])
        return self.planificacion.cupo - len(reservas)

    def cupos_disponible_planificacion(self):
        reservas = self.reservacionturnospoli_set.filter(status=True,
                                                        fechareservacion__reservacion__estado__in=[1, 2, 4]).values_list('fechareservacion__reservacion_id').\
                                                        order_by('fechareservacion__reservacion_id').distinct()
        return self.planificacion.cupo - len(reservas)

    def horario_disponible(self, fecha):
        disponible = True
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        if fecha == datetime.now().date():
            if datetime.now().time() > self.turno.comienza:
                disponible = False
        return disponible

    def fechas_horarios(self):
        return self.fechainicio.strftime('%d-%m-%Y') + " al " + self.fechafin.strftime('%d-%m-%Y')

    class Meta:
        verbose_name = u"Horario de instructor"
        verbose_name_plural = u"Horarios de instructores"


class ReservacionPersonaPoli(ModeloBase):
    codigo = models.CharField(max_length=20, verbose_name='Codigo de turno generado', blank=True, null=True)
    area = models.ForeignKey(AreaPolideportivo, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Área')
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    familiar = models.ForeignKey('sga.PersonaDatosFamiliares', verbose_name=u'Familiar', blank=True, null=True, on_delete=models.PROTECT)
    perfil = models.ForeignKey('sga.PerfilUsuario', blank=True, null=True, verbose_name=u'Perfil Persona',
                               on_delete=models.CASCADE)
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, verbose_name=u'Inscripción',
                                    on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_RESERVA_POLIDEPORTIVO, default=1, verbose_name=u'Estado')
    finicialreserva = models.DateField(blank=True, null=True, verbose_name='Fecha Inicial Reservación')
    ffinalreserva = models.DateField(blank=True, null=True, verbose_name='Fecha Final Reservación')
    fechaexpira = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha Expira Reservación')
    actividad = models.ForeignKey(ActividadPolideportivo, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Actividad Polideportivo')
    planificacion = models.ForeignKey(PlanificacionActividad, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Planificación de actividad')
    tercero = models.BooleanField(default=False, verbose_name=u'Reservacion para terceros')
    tipotercero = models.IntegerField(choices=TIPO_TERCERO, blank=True, null=True, verbose_name=u'Tipo de personas extras')
    cantidad = models.IntegerField(default=0, verbose_name=u'Cantidad de Personas extras')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'observación')
    asistio = models.BooleanField(default=False, verbose_name=u'Asistencia de Reserva')
    archivo = models.FileField(upload_to='unemideporte/comprobantes', blank=True, null=True, verbose_name=u'Comprobante de Pago')

    def get_datos_reporte_encuesta_satisfaccion(self):
        return {
            'solicitante': self.persona.nombre_completo_inverso(),
            'tipousuario': self.perfil.__str__(),
            'cargo': '',
            'cedula': self.persona.cedula,
            'correo': self.persona.emailinst if self.persona.emailinst else self.persona.email,
            'requerimiento': self.area.nombre,
            'fecha': self.fecha_creacion.strftime('%d/%m/%Y') if self.fecha_creacion else '',
            'asiganadoa': '',
        }

    def dias_disponibles(self):
        try:
            rangofechasstr, rangofechas, fechahasta, fechadesde = [], [], self.ffinalreserva, self.finicialreserva
            for day in range((fechahasta - fechadesde).days + 1):
                fechafiltro = fechadesde + timedelta(days=day)
                # rangofechas.append("{} {}".format((fechadesde + timedelta(days=day)).strftime("%d"), (fechadesde + timedelta(days=day)).strftime("%b")))
                rangofechas.append(fechafiltro)
            return rangofechas
        except Exception as ex:
            return []

    def familiares(self):
        return ReservacionTercerosPoli.objects.filter(reservacion__fechareservacion__reservacion=self, status=True)

    def implemento_sugerido(self):
        self.actividad.implementos()

    def implemento_entregado(self):
        self.implementosreservacionpersona_set.filter(status=True)

    def get_turnoservado(self):
        return ReservacionTurnosPoli.objects.filter(fechareservacion__reservacion=self, status=True,
                                                    fechareservacion__reservacion__planificacion__isnull=True).first()

    def turno_reservado(self):
        reservaturno = False
        if ReservacionTurnosPoli.objects.filter(fechareservacion__reservacion=self).exists():
            reservaturno = ReservacionTurnosPoli.objects.get(fechareservacion__reservacion=self)
        return reservaturno

    def puede_cancelar(self):
        puede = True
        fechaactual = (datetime.now() + timedelta(minutes=14))
        reservaturno = self.turno_reservado()
        turno = reservaturno.turno.turno.comienza
        if self.estado != 1 and self.estado != 2:
            puede = False
        elif datetime.now().date() > self.finicialreserva:
            puede = False
        elif fechaactual.time() > turno and datetime.now().date() == self.finicialreserva:
            puede = False
        return puede

    def color_estado(self):
        color = 'bg-default'
        if self.estado == 2:
            color = "bg-success"
        if self.estado == 3:
            color = "bg-danger"
        if self.estado == 4:
            color = "bg-secondary"
        return color

    def color_estado_text(self):
        color = 'text-default'
        if self.estado == 2:
            color = "text-success"
        if self.estado == 3:
            color = "text-danger"
        if self.estado == 4:
            color = "text-secondary"
        return color

    def respuestas_encuesta(self):
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self)
        return RespuestaEncuestaSatisfaccion.objects.filter(object_id=self.id, content_type=content_type, status=True)

    def __str__(self):
        return "{} ({})".format(self.persona, self.actividad.nombre)

    class Meta:
        verbose_name = u"Reservación Área Polideportivos"
        verbose_name_plural = u"Reservación Áreas Polideportivos"


class ObservacionReservacionPersona(ModeloBase):
    reservacion = models.ForeignKey(ReservacionPersonaPoli, on_delete=models.PROTECT, blank=True, null=True,
                                    verbose_name='Reservación')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'observación')

    def __str__(self):
        return "{} - {}".format(str(self.reservacion), self.observacion)

    class Meta:
        verbose_name = u"Observación de reservación"
        verbose_name_plural = u"Observaciones de reservación"


class ImplementosReservacionPersona(ModeloBase):
    reservacion = models.ForeignKey(ReservacionPersonaPoli, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Reservación')
    implemento = models.ForeignKey(ImplementosActividad, on_delete=models.PROTECT, blank=True, null=True, verbose_name=u'Implemento')
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad")

    def __str__(self):
        return "{} - {}".format(str(self.reservacion), self.implemento)

    class Meta:
        verbose_name = u"Implemento de reservación"
        verbose_name_plural = u"Implementos de reservación"


class ReservacionFechasPoli(ModeloBase):
    reservacion = models.ForeignKey(ReservacionPersonaPoli, on_delete=models.PROTECT, blank=True, null=True,
                                    verbose_name='Reservación')
    freservacion = models.DateField(blank=True, null=True, verbose_name='Fecha Reservación')

    def __str__(self):
        return "{} - {}".format(str(self.freservacion), self.reservacion.persona)

    def puede_eliminar(self):
        if self.reservacionturnospoli_set.filter(status=True):
            return False
        return True

    class Meta:
        verbose_name = u"Reservación Fecha Área"
        verbose_name_plural = u"Reservaciones Fechas Áreas"


class ReservacionTurnosPoli(ModeloBase):
    fechareservacion = models.ForeignKey(ReservacionFechasPoli, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Reservación')
    turno = models.ForeignKey(HorarioActividadPolideportivo, blank=True, null=True, verbose_name=u'Turno', on_delete=models.CASCADE)
    seccion = models.ManyToManyField(SeccionPolideportivo, verbose_name=u'Secciones')
    asistio = models.BooleanField(default=False, verbose_name=u'Aisitio tercero')

    def __str__(self):
        return "{} {} {}".format(self.fechareservacion.freservacion, self.turno, self.turno.actividad.area)

    def pendiente(self):
        pendiente = False
        if self.fechareservacion.reservacion.finicialreserva >= datetime.now().date():
            pendiente = True
        return pendiente

    def cantidad_reservas(self):
        return self.fechareservacion.reservacion.cantidad + len(self.reservaciontercerospoli_set.filter(status=True)) + 1

    def reserva_terceros(self):
        terceros = self.reservaciontercerospoli_set.filter(status=True)
        limitada = terceros[:3]
        cantidad = len(terceros)
        diccionario = {'limitada': limitada, 'cantidad': cantidad, 'terceros': terceros}
        return diccionario

    class Meta:
        verbose_name = u"Reservación Turno Área"
        verbose_name_plural = u"Reservación Turno Áreas"


class ReservacionTercerosPoli(ModeloBase):
    reservacion = models.ForeignKey(ReservacionTurnosPoli, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Reservación Turnos Poli')
    familiar = models.ForeignKey('sga.PersonaDatosFamiliares', verbose_name=u'Familiar', blank=True, null=True, on_delete=models.PROTECT)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Acompañante', blank=True, null=True, on_delete=models.PROTECT)
    asistio = models.BooleanField(default=False, verbose_name=u'Aisitio tercero')

    def __str__(self):
        companero = ''
        if self.familiar:
            companero = self.familiar
        elif self.persona:
            companero = self.persona
        return "{} ({})".format(self.reservacion, companero)


class ReservacionSeccionPoli(ModeloBase):
    reservacionturno = models.ForeignKey(ReservacionTurnosPoli, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Reservación Turnos')
    seccion = models.ForeignKey(SeccionPolideportivo, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Seccion')
    cantidad = models.IntegerField(verbose_name=u'Cantidad', default=0)

    def __str__(self):
        return "{} {}".format(self.seccion, self.reservacionturno.turno.actividad.area)

    class Meta:
        verbose_name = u"Reservación Seccion Area"
        verbose_name_plural = u"Reservación Seccion Áreas"


class ClubPoli(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name='Nombre del club', blank=True, null=True)
    finicio = models.DateField(blank=True, null=True, verbose_name='Fecha Inicial del CLub')
    ffin = models.DateField(blank=True, null=True, verbose_name='Fecha Final del Club')
    responsable = models.ForeignKey('sga.Persona', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Responsable a cargo del club')
    disciplina = models.ForeignKey('sga.DisciplinaDeportiva', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Disciplina de club')
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name=u'Descripción del club')

    def __str__(self):
        return "{}".format(self.nombre)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.capitalize().strip()
        super(ClubPoli, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Club Poli"
        verbose_name_plural = u"Clubes Poli"


TIPO_INTEGRANTE = ((1, 'Deportista'), (2, 'Instructor'), (3, 'Directivo'),)


class IntegranteClubPoli(ModeloBase):
    club = models.ForeignKey(ClubPoli, on_delete=models.CASCADE, verbose_name='Club al que pertenece')
    integrante = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name='Integrante del club')
    tipointegrante = models.IntegerField(choices=TIPO_INTEGRANTE, blank=True, null=True, verbose_name=u'Tipo de integrante del club')

    def __str__(self):
        return "{}-{}".format(self.integrante, self.club)

    class Meta:
        verbose_name = u"Integrante de Club"
        verbose_name_plural = u"Integrates de Club"


class SeleccionadosClubPoli(ModeloBase):
    integranteclub = models.ForeignKey(IntegranteClubPoli, on_delete=models.CASCADE, verbose_name='Integrante perteneciente a la seleccion')

    def __str__(self):
        return "{}".format(self.seleccionado)

    class Meta:
        verbose_name = u"Seleccionado del Club"
        verbose_name_plural = u"Seleccionados del Club"


class DescuentoValorActividad(ModeloBase):
    perfilactividad = models.ForeignKey(PerfilesActividad, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Perfil actividad por aplicar el descuento')
    familiar = models.ManyToManyField(ParentescoPersona, verbose_name='Familiar al cual aplica el descuento')
    porcentaje = models.IntegerField(default=0, verbose_name='Porcentaje de descuento')
    valor_descuento = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name='Valor del descuento')
    valor_final = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name='Valor final a cancelar')
    aplicavigencia = models.BooleanField(default=False, verbose_name='Aplica vigencia de descuento por fechas')
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha que inicia el descuento')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha que finaliza el descuento')
    publicado = models.BooleanField(default=False, verbose_name='El descuento esta publicado')

    def __str__(self):
        return "{} - {}".format(self.porcentaje, self.perfilactividad)

    class Meta:
        verbose_name = u"Descuento Valor Actividad"
        verbose_name_plural = u"Descuentos Valor Actividad"


SECCION = (
    (1, u'Formativas'),
    (2, u'Espacios Deportivos'),
    (3, u'Vacacionales'),
    (4, u'Noticias'),
    (5, u'Logros'),
    (6, u'Nuestro Equipo'),
)
UBICACION = (
    (1, u'Superior'),
    (2, u'Inferior'),
)
class TituloWebSite(ModeloBase):
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo principal de la sección')
    subtitulo = models.CharField(default='', max_length=100, verbose_name=u'Subtitulo de la sección')
    seccion = models.IntegerField(blank=True, null=True, choices=SECCION, verbose_name="Sección donde se colocara el texto")
    publicado = models.BooleanField(default=False, verbose_name='El titulo esta publicado')
    fondotitulo = models.FileField(upload_to='unemideporte', blank=True, null=True, verbose_name=u'Fondo del titulo')

    def __str__(self):
        return f'{self.titulo}'

    def get_titulo(self):
        if not self.titulo:
            if self.seccion == 1:
                return 'Nuestras Escuelas Formativas'
            if self.seccion == 2:
                return 'Nuestros Espacios Deportivos'

    def get_fondo(self):
        if not self.fondotitulo:
            return '/static/images/polideportivo/escuelasformativas.png'
        else:
            return self.fondotitulo.url

    def cuerpos_top(self):
        return self.cuerpowebsite_set.filter(status=True, ubicacion=1).order_by('orden')

    def cuerpos_bottom(self):
        return self.cuerpowebsite_set.filter(status=True, ubicacion=2).order_by('orden')

    class Meta:
        verbose_name = u"Titulo Web Site"
        verbose_name_plural = u"Titulos Web Site"

class CuerpoWebSite(ModeloBase):
    titulowebsite = models.ForeignKey(TituloWebSite, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Titulo del website')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo del cuerpo de sección')
    descripcion = models.TextField(default='', max_length=5000, verbose_name=u'Descripción')
    ubicacion = models.IntegerField(blank=True, null=True, choices=UBICACION, verbose_name="Ubicación donde se colocara el texto")
    publicado = models.BooleanField(default=False, verbose_name='El cuerpo esta publicado')
    orden = models.IntegerField(default=0, verbose_name='Orden')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Cuerpo Web Site"
        verbose_name_plural = u"Cuerpos Web Site"

class NoticiaDeportiva(ModeloBase):
    titulo = models.CharField(default='', max_length=200, verbose_name=u'Titulo principal de la noticia')
    subtitulo = models.CharField(default='', max_length=200, verbose_name=u'Subtitulo de la noticia')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    principal = models.BooleanField(default=False, verbose_name='Es una noticia principal')
    portada = models.FileField(upload_to='unemideporte/noticias', blank=True, null=True, verbose_name=u'Portada de noticia')
    publicado = models.BooleanField(default=False, verbose_name='El cuerpo esta publicado')

    def __str__(self):
        return f'{self.titulo}'

    def get_fondo(self):
        if not self.portada:
            return '/static/images/polideportivo/escuelasformativas.png'
        else:
            return self.portada.url

    def publicar_text(self):
        if not self.publicado:
            return 'publicar'
        else:
            return 'quitar publicación'

    def principal_text(self):
        if not self.principal:
            return 'Estas por cambiar el tipo de notícia a principal'
        else:
            return 'Estas por cambiar el tipo de notícia a general'

    def puede_cambiar_tipo(self):
        if not self.principal:
            noticias = NoticiaDeportiva.objects.filter(status=True, principal=True, publicado=True)
            return len(noticias) < 3
        return True

    def puede_cambiar_tipo_original(self):
        if self.principal:
            noticias = NoticiaDeportiva.objects.filter(status=True, principal=True, publicado=True)
            return len(noticias) < 3
        return True

    class Meta:
        verbose_name = u"Noticia Deportiva"
        verbose_name_plural = u"Noticias Deportivas"

class CuerpoNoticiaDeportiva(ModeloBase):
    noticia = models.ForeignKey(NoticiaDeportiva, on_delete=models.CASCADE, verbose_name='Noticia')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo principal del cuerpo de noticia')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    orden = models.IntegerField(default=0, verbose_name='Orden')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Cuerpo Noticia Deportiva"
        verbose_name_plural = u"Cuerpo de Noticias Deportivas"

class FotoCuerpoNoticia(ModeloBase):
    cuerpo = models.ForeignKey(CuerpoNoticiaDeportiva, on_delete=models.CASCADE, verbose_name='Cuerpo de noticia')
    orden = models.IntegerField(default=0, verbose_name='Orden')
    foto = models.FileField(upload_to='unemideporte/noticias', blank=True, null=True, verbose_name=u'Foto')
    titulo = models.CharField(default='', max_length=100, verbose_name=u'Titulo de la imagen')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        verbose_name = u"Foto de Cuerpo Noticia"
        verbose_name_plural = u"Fotos de Cuerpo de Noticias"

class InstitucionEscuela(ModeloBase):
    from sga.models import Canton, Pais, Provincia, Parroquia, TipoColegio
    tipo = models.ForeignKey(TipoColegio, blank=True, null=True, verbose_name=u"Tipo de escuela", on_delete=models.CASCADE)
    nombre = models.TextField(default='', verbose_name=u'Nombre de la escuela')
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'País', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u'Provincia', on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u'Canton', on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, verbose_name=u"Parroquia", on_delete=models.CASCADE)
    validada = models.BooleanField(default=False, verbose_name='Institución Validada')

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.tipo.nombre.upper())

    class Meta:
        verbose_name = u"Escuela"
        verbose_name_plural = u"Escuelas"

class PersonaPrimaria(ModeloBase):
    from sga.models import Persona
    persona = models.ForeignKey(Persona, verbose_name=u'Persona', blank=True, null=True, on_delete=models.CASCADE)
    escuela = models.ForeignKey(InstitucionEscuela, blank=True, null=True, verbose_name=u'Escuela', on_delete=models.CASCADE)
    anios = models.IntegerField(default=0, verbose_name=u'Años cursados')
    inicio = models.DateField(blank=True,null=True, verbose_name='Fecha que inicio su estudio')
    fin = models.DateField(blank=True,null=True, verbose_name='Fecha que finalizo su estudio')
    cursando = models.BooleanField(default=False, verbose_name=u'Cursando')

    def __str__(self):
        return f'{self.escuela}'

    class Meta:
        verbose_name = u"Primaria de persona"
        verbose_name_plural = u"Primarias de persona"
