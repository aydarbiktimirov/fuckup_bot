#!/usr/bin/env python3

import urllib.request
import traceback
import datetime
import socket
import time

import abc

import models


class Monitor(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def check(self, bot, chat):
        pass

    @abc.abstractmethod
    def on_fail(self, bot, chat, fail_info=None):
        pass

    def on_success(self, bot, chat):
        pass

    @abc.abstractmethod
    def to_json(self):
        pass

    def from_json(description):
        cls = description.pop('__class__')
        return globals()[cls](**description)


def start(bot):
    while True:
        try:
            for chat in models.Chat.objects:
                print('{} has {} active monitorings'.format(chat.id, len(chat.monitors)))
                for i, monitor in enumerate(chat.monitors):
                    try:
                        Monitor.from_json(monitor).check(bot, chat, i)
                    except:
                        traceback.print_exc()
        except:
            traceback.print_exc()
        time.sleep(5)


class HttpMonitor(Monitor):
    def __init__(self, name, endpoint, method=None, timeout=None, data=None, expected_response=None, idx=None):
        self.name = name
        self.endpoint = endpoint
        self.data = data
        self.method = method
        self.timeout = timeout
        self.expected_response = expected_response
        self.idx = idx

    def check(self, bot, chat, idx):
        self.idx = idx
        try:
            request = urllib.request.Request(self.endpoint, method=self.method)
            result = urllib.request.urlopen(request, data=self.data.encode('utf8') if self.data is not None else None, timeout=self.timeout)
            response = result.read().decode('utf8')
            if self.expected_response is not None and self.expected_response != response:
                self.on_fail(bot, chat, {'error': 'unexpected response', 'response': response})
                return
            self.on_success(bot, chat)
        except socket.timeout:
            self.on_fail(bot, chat, {'error': 'timeout'})
        except Exception as e:
            try:
                self.on_fail(bot, chat, {'error': 'code', 'msg': str(e), 'code': result.getcode()})
            except:
                traceback.print_exc()
                self.on_fail(bot, chat, {'error': 'other', 'msg': str(e)})

    def on_fail(self, bot, chat, fail_info):
        status = models.MonitorStatus.get(chat, self.idx)
        status.unsuccessful_runs_in_a_row += 1
        if status.unsuccessful_runs_in_a_row >= 5 and (
            not status.dont_report_until or
            status.dont_report_until <= datetime.datetime.now()
        ):
            status.dont_report_until = datetime.datetime.now() + datetime.timedelta(minutes=5)
            bot.sendMessage(
                chat_id=chat.id,
                text=self.format_error_message(fail_info),
                parse_mode='markdown',
            )
        status.save()

    def on_success(self, bot, chat):
        status = models.MonitorStatus.get(chat, self.idx)
        status.unsuccessful_runs_in_a_row = 0
        status.dont_report_until = None
        status.save()
        print('{}({}) passed for {}'.format(type(self).__name__, self.endpoint, chat.id))

    def to_json(self):
        res = vars(self)
        res['__class__'] = type(self).__name__
        return res

    def format_error_message(self, fail_info):
        if fail_info['error'] == 'timeout':
            return '{name}: *Timed out* during request to [{url}]({url})\nTimeout = {timeout}s'.format(url=self.endpoint, name=self.name, timeout=self.timeout)
        elif fail_info['error'] == 'code':
            return '{name}: *Bad response code* during request to [{url}]({url})\nResponse code = {code}'.format(url=self.endpoint, name=self.name, code=fail_info['code'])
        elif fail_info['error'] == 'unexpected response':
            return '{name}: *Unexpected response* during request to [{url}]({url})\nExpected = {exp}\nActual = {act}'.format(url=self.endpoint, name=self.name, exp=self.expected_response, act=fail_info['response'])
        else:
            return '{name}: *Unknown error* during request to [{url}]({url})\nError message = `{msg}`'.format(url=self.endpoint, name=self.name, msg=fail_info['msg'])
