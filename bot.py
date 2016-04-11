#!/usr/bin/env python3

import threading
import traceback
import time
import json

import telegram

import monitors
import models


TOKEN = '<YOUR TOKEN>'


class Bot(telegram.Bot):
    def on_update(self, update):
        chat = models.Chat.get(update.message.chat.id)
        if update.message.text:
            if update.message.text == '/info':
                self.sendMessage(
                    chat_id=update.message.chat.id,
                    text='Active monitorings:\n{}'.format('\n'.join(
                        str(i) + ' — ' + json.dumps(monitor, sort_keys=True, indent=2, ensure_ascii=False)
                        for i, monitor in enumerate(chat.monitors)
                    )),
                )
            elif update.message.text.startswith('/add '):
                monitor = monitors.Monitor.from_json(json.loads(
                    update.message.text[len('/add '):],
                ))
                chat.monitors.append(monitor.to_json())
                chat.save()
                self.sendMessage(
                    chat_id=update.message.chat.id,
                    text='Active monitorings:\n{}'.format('\n'.join(
                        str(i) + ' — ' + json.dumps(monitor, sort_keys=True, indent=2, ensure_ascii=False)
                        for i, monitor in enumerate(chat.monitors)
                    )),
                )
            elif update.message.text.startswith('/edit '):
                parts = update.message.text.split(' ', 2)
                monitor = monitors.Monitor.from_json(json.loads(parts[2]))
                chat.monitors[int(parts[1])] = monitor.to_json()
                chat.save()
                self.sendMessage(
                    chat_id=update.message.chat.id,
                    text='Active monitorings:\n{}'.format('\n'.join(
                        str(i) + ' — ' + json.dumps(monitor, sort_keys=True, indent=2, ensure_ascii=False)
                        for i, monitor in enumerate(chat.monitors)
                    )),
                )
            elif update.message.text.startswith('/del '):
                del chat.monitors[int(update.message.text[len('/del '):])]
                chat.save()
                models.MonitorState.objects(chat=chat).delete()
                self.sendMessage(
                    chat_id=update.message.chat.id,
                    text='Active monitorings:\n{}'.format('\n'.join(
                        str(i) + ' — ' + json.dumps(monitor, sort_keys=True, indent=2, ensure_ascii=False)
                        for i, monitor in enumerate(chat.monitors)
                    )),
                )

    def start(self, polling=True):
        if polling:
            update_id = None
            self.setWebhook('')
            while True:
                try:
                    updates = self.getUpdates(update_id)
                except:
                    updates = []
                time.sleep(.2)
                for update in updates:
                    update_id = update.update_id + 1
                    if update.message:
                        try:
                            self.on_update(update)
                        except:
                            traceback.print_exc()
        else:
            raise NotImplemented('Not yet')

    def start_monitors(self):
        thread = threading.Thread(target=monitors.start, args=(self,))
        thread.start()


def main():
    import mongoengine
    mongoengine.connect('monitoring_bot')
    bot = Bot(token=TOKEN)
    bot.start_monitors()
    bot.start()


if __name__ == '__main__':
    main()
