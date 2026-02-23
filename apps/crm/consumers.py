import json

from channels.generic.websocket import AsyncWebsocketConsumer


class KanbanConsumer(AsyncWebsocketConsumer):
    GROUP = "kanban_board"

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass  # clients are read-only; they never send to the server

    async def kanban_card_update(self, event):
        """Relay a card_update event pushed by the Django layer to the WebSocket client."""
        await self.send(text_data=json.dumps(event["data"]))
