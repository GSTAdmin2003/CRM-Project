import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.pk = self.scope['url_route']['kwargs']['pk']
        self.group_name = f'chat_{self.pk}'

        if not self.scope['user'].is_authenticated:
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    # Receive signal from channel layer → forward to WebSocket client
    def chat_update(self, event):
        self.send(text_data=json.dumps({'type': 'update'}))
