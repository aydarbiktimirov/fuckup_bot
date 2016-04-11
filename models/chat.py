#!/usr/bin/env python3

from mongoengine import *


class Chat(Document):
    id = IntField(primary_key=True)
    state = StringField(default='start')
    properties = DictField(default={})
    monitors = ListField(default=[])
    fake_flag = BooleanField(required=False)

    @staticmethod
    def get(chat_id):
        chat = Chat.objects(id=chat_id)
        chat.update(upsert=True, unset__fake_flag='')
        return chat.first()


class MonitorStatus(Document):
    chat = ReferenceField(Chat)
    monitor_idx = IntField()
    unsuccessful_runs_in_a_row = IntField(default=0)
    dont_report_until = DateTimeField(required=False)
    fake_flag = BooleanField(required=False)

    meta = {
        'indexes': [
            'chat',
            ('chat', 'monitor_idx'),
        ],
    }

    @staticmethod
    def get(chat, idx):
        status = MonitorStatus.objects(chat=chat, monitor_idx=idx)
        status.update(upsert=True, unset__fake_flag='')
        return status.first()
