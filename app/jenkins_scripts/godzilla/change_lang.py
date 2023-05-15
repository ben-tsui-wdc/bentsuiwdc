# -*- coding: utf-8 -*-
""" Tool for change language.
"""
# std modules
import logging
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient
class ChangeLang(object):

    def __init__(self, parser):
        self.skip_if_lang = parser.skip_if_lang
        self.change_lang = parser.change_lang

        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()
 
    def main(self):
        if self.skip_if_lang:
            if self.skip_if_lang == self.ssh_client.get_current_lang(): return
        if self.change_lang:
            if not self.ssh_client.change_lang(self.change_lang):
                raise AssertionError('Change lang fail')


if __name__ == '__main__':
    parser = ArgumentParser("""\
        *** Change language ***
        """)
    parser.add_argument('-ssh_ip', '--ssh_ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-sil', '--skip-if-lang', help='Skip process if now device is using specifying language', metavar='LANG', default=None)
    parser.add_argument('-cl', '--change-lang', help='Change device to use specifying language', default=None,
        choices=['cs-CZ', 'de-DE', 'en-US', 'es-ES', 'fr-FR', 'hu-HU', 'it_IT', 'ja-JP', 'ko-KR', 'nl-NL', 'no-NO', 'pl-PL', 'pt-BR', 'ru-RU', 'sv-SE', 'tr-TR', 'zh-CN', 'zh-TW'])
    ChangeLang(parser.parse_args()).main()
