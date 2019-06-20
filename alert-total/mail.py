#!/usr/bin/env python

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


class SMTPServer(smtplib.SMTP_SSL, object):
    def __init__(self, username, password, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self.login(username, password)
        self.from_addr = username

    def send_message(self, from_username, to_addrs, subject, body, attachments=[]):
        msg = MIMEMultipart()
        msg['From'] = '{} <{}>'.format(from_username, self.from_addr)
        msg['To'] = COMMASPACE.join(to_addrs)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        for attachment in attachments:
            with open(attachment, 'rb') as fd:
                part = MIMEApplication(
                    fd.read(),
                    Name=os.path.basename(attachment)
                )
                part['Content-Disposition'] = 'attachment; filename="{}"'.format(os.path.basename(attachment))
                msg.attach(part)

        self.sendmail(self.from_addr, to_addrs, msg.as_string())
