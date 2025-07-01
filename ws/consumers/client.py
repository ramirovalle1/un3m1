import json
import django
django.setup()
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q, Sum
from api.serializers.alumno.notificacion import NotificacionSerializer
from sga.models import Notificacion
from datetime import datetime


class ClientConsumer(AsyncWebsocketConsumer):
    groups = ["general"]

    async def connect(self):
        if self.scope["user"] is not AnonymousUser:
            self.user_id = self.scope["user"].id
            await self.channel_layer.group_add(f"{self.user_id}", self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            f"{self.user_id}",
            self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        type = text_data_json['type']
        datos = text_data_json['datos']

        # Send message to room group
        await self.channel_layer.group_send(
            self.key_room_group,
            {
                'type': type,
                'message': message,
                'datos': datos
            }
        )

    async def cargar_ultimas_notificaciones(self, event):
        message = event['message']
        type = event['type']
        datos = event['datos']
        persona_id = datos.get('persona_id')
        perfilusuario_id = datos.get('perfilusuario_id')
        eNotificaciones = await self.get_latest_notifications(persona_id, perfilusuario_id)
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type,
            'datos': eNotificaciones
        }))

    @database_sync_to_async
    def get_latest_notifications(self, persona_id, perfilusuario_id):
        hoy = datetime.now()
        eNotificaciones = Notificacion.objects.filter(Q(app_label='SIE'), destinatario_id=persona_id, perfil_id=perfilusuario_id, leido=False, visible=True, fecha_hora_visible__gte=hoy)[0:5]
        return NotificacionSerializer(eNotificaciones, many=True).data if eNotificaciones.values("id").exists() else []

    async def demo_init(self, event):
        message = event['message']
        type = event['type']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type
        }))

    # async def send_last_message(self, event):
    #     last_msg = await self.get_last_message(self.user_id)
    #     last_msg["status"] = event["text"]
    #     await self.send(text_data=json.dumps(last_msg))

    # @database_sync_to_async
    # def get_last_message(self, user_id):
    #     message = Message.objects.filter(user_id=user_id).last()
    #     return message.message
