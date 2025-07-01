from sga.models import Persona, Inscripcion


class My_Persona(Persona):

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_Persona, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_Persona, self).save(*args, **kwargs)