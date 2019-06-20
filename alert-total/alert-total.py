#!/usr/bin/env python

import datetime
import sys
import time
from collections import Counter

import jinja2
from pyzabbix import ZabbixAPI

from config import SMTP_CONFIG, EMAIL_RECEIVERS, ZABBIX
from mail import SMTPServer


zapi = ZabbixAPI('http://{}'.format(ZABBIX['address']))
zapi.login(ZABBIX['user'], ZABBIX['password'])
print('Connected to Zabbix API Version {}'.format(zapi.api_version()))

SEVERITY = {
    2: 'P3',
    3: 'P2',
    4: 'P1',
    5: 'P0'
}


def get_groups():
    groups = zapi.hostgroup.get(
        real_hosts='true', monitored_hosts='true',
        output=['groupid', 'name'])
    return {group['groupid']: group['name'] for group in groups}


def get_media():
    output = {
        media.get('mediatypeid', -1): media.get('description', '-')
        for media in zapi.mediatype.get(output=['mediatypeid', 'description'])
    }
    return output


def get_alert(eventids, medias):
    output = [
        medias.get(mediatypeids.get('mediatypeid', '-1'))
        for mediatypeids in zapi.alert.get(eventids=eventids, output=['mediatypeid'])
    ]
    return dict(Counter(output))


def get_event(groupid, severities, time_from, time_till):
    output = {
        eventid.get('eventid'): eventid.get('objectid')
        for eventid in zapi.event.get(
            groupids=groupid, value=1, severities=severities,
            time_from=time_from, time_till=time_till,
            output=['eventid', 'objectid']
        )}
    return output


def get_trigger(objectids):
    triggers = [
        zapi.trigger.get(triggerids=objectid, output=['description'])[0].get('description')
        for objectid in objectids
    ]
    return sorted(dict(Counter(triggers)).items(), key=lambda b: b[1], reverse=True)


def get_times(days):
    time_now = time.time()
    time_from = time_now - days * 24 * 60 * 60
    return time_from, time_now


def main(days):
    medias = get_media()
    time_from, time_now = get_times(days)
    cache, cache_count = {}, {}
    for groupid, group_name in get_groups().items():
        for severityid, severity_name in SEVERITY.items():
            eventids = get_event(groupid, severityid, time_from, time_now)
            media_count = get_alert(list(eventids.keys()), medias)
            triggers = get_trigger(list(eventids.values()))
            if len(media_count) > 0:
                cache.setdefault(group_name, {}).setdefault(severity_name, {}).setdefault('media_count', media_count)
                cache.setdefault(group_name, {}).setdefault(severity_name, {}).setdefault('triggers', triggers)
        media_sum = sum([s for values in cache.get(group_name, {}).values() for s in values['media_count'].values()])
        cache_count.setdefault(group_name, media_sum)
    dt = [
        time.strftime('%Y-%m-%d:%H', time.localtime(time_from)),
        time.strftime('%Y-%m-%d:%H', time.localtime(time_now))]
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('./src/templates', 'utf8'))
    template = env.get_template('alert-total.html')
    text = template.render(cache=cache, cache_count=cache_count, dt=dt)
    smtp = SMTPServer(**SMTP_CONFIG)
    smtp.send_message(
        'Infrastructure',
        ['{}@growingio.com'.format(i) for i in EMAIL_RECEIVERS],
        'Zabbix Alerts - Weekly Report', text, []
    )


if __name__ == '__main__':
    days = 1 if len(sys.argv) < 2 else float(sys.argv[1])
    main(days)
