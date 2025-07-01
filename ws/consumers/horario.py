import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class HorarioConsumer(AsyncWebsocketConsumer):
    groups = ["clases"]

    async def connect(self):
        if self.scope["user"] is not AnonymousUser:
            self.key_room = self.scope['url_route']['kwargs']['key_room']
            self.key_room_group = 'room_%s' % self.key_room
            await self.channel_layer.group_add(self.key_room_group, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.key_room_group,
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

    async def puede_entrar_clases(self, event):
        message = event['message']
        type = event['type']
        datos = event['datos']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type,
            'datos': datos
        }))

    async def entro_clase(self, event):
        message = event['message']
        type = event['type']
        datos = event['datos']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'type': type,
            'datos': datos,
        }))

    # async def send_last_message(self, event):
    #     last_msg = await self.get_last_message(self.user_id)
    #     last_msg["status"] = event["text"]
    #     await self.send(text_data=json.dumps(last_msg))

    # @database_sync_to_async
    # def get_last_message(self, user_id):
    #     message = Message.objects.filter(user_id=user_id).last()
    #     return message.message
