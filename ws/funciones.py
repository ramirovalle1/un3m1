from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notificar_usuario_notificaciones(grupo, persona_id, perfilusuario_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(grupo, {"type": "send_lastest_notifications",
                                                    "message": "ping",
                                                    "datos": {"persona_id": persona_id, "perfilusuario_id": perfilusuario_id}}
                                            )