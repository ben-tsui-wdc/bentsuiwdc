# -*- coding: utf-8 -*-
""" Tool for user group.
"""
# std modules
import logging
import sys
from argparse import ArgumentParser

# platform modules
from platform_libraries.ssh_client import SSHClient


class UserGroup(object):

    def __init__(self, parser):
        self.reset_admin = parser.reset_admin
        self.admin_password = parser.admin_password
        self.delete_users = parser.delete_users
        self.delete_groups = parser.delete_groups
        self.delete_shares = parser.delete_shares
        self.delete_user_prename = parser.delete_user_prename
        self.delete_user_start_index = parser.delete_user_start_index
        self.delete_user_total = parser.delete_user_total
        self.check_user_prename = parser.check_user_prename
        self.check_user_start_index = parser.check_user_start_index
        self.check_user_total = parser.check_user_total
        self.delete_group_prename = parser.delete_group_prename
        self.delete_group_start_index = parser.delete_group_start_index
        self.delete_group_total = parser.delete_group_total
        self.ssh_client = SSHClient(parser.ssh_ip, parser.ssh_user, parser.ssh_password, parser.ssh_port)
        self.ssh_client.connect()

    def main(self):
        if self.reset_admin: self.reset_admin_to_default()
        if self.delete_users:
            self.delete_for_each(del_func=self.ssh_client.delete_user, values=self.delete_users)
            self.delete_for_each(del_func=self.ssh_client.delete_share, values=self.delete_users)
        if self.delete_groups: self.delete_for_each(del_func=self.ssh_client.delete_group, values=self.delete_groups)
        if self.delete_shares: self.delete_for_each(del_func=self.ssh_client.delete_share, values=self.delete_shares)
        if self.delete_user_prename and self.delete_user_start_index and self.delete_user_total:
            if not self.ssh_client.delete_continuous_users(self.delete_user_prename, self.delete_user_start_index, self.delete_user_total):
                return False
        if self.check_user_prename and self.check_user_start_index and self.check_user_total:
            if not self.ssh_client.check_continuous_users(self.check_user_prename, self.check_user_start_index, self.check_user_total):
                return False
        if self.delete_group_prename and self.delete_group_start_index and self.delete_group_total:
            if not self.ssh_client.delete_continuous_groups(self.delete_group_prename, self.delete_group_start_index, self.delete_group_total):
                return False

    def reset_admin_to_default(self):
        self.ssh_client.log.info('Reset admin user name to admin and password to adminadmin')
        admin_record, _ = self.ssh_client.execute_cmd('cat /etc/passwd | grep "500:1000"')
        admin_name = admin_record.split(':', 1)[0]
        if admin_name != 'admin':
            self.ssh_client.execute_cmd('account -u "{}" -n "admin"'.format(admin_name))
        self.ssh_client.execute_cmd('account -m -u "admin" -p "{}"'.format(self.admin_password))

    def delete_for_each(self, del_func, values):
        for v in values:
            del_func(v)


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Script for user group ***
        """)

    parser.add_argument('-ssh_ip', '--ssh_ip', help='The hostname of SSH server', metavar='IP')
    parser.add_argument('-ssh_user', '--ssh_user', help='The username of SSH server', default="sshd")
    parser.add_argument('-ssh_password', '--ssh_password', help='The password of SSH server', metavar='PWD', default="Test1234")
    parser.add_argument('-ssh_port', '--ssh_port', help='The port of SSH server', type=int, metavar='PORT', default=22)
    parser.add_argument('-ra', '--reset_admin', help='To reset admin', action='store_true', default=False)
    parser.add_argument('-ap', '--admin_password', help='admin password to restore', default="adminadmin")
    parser.add_argument('-du', '--delete_users', nargs='*', help='User names to be deleted e.g., -du user1 user2', metavar='USERS', default=None)
    parser.add_argument('-dg', '--delete_groups', nargs='*', help='Group names to be deleted e.g., -dg group1 group2', metavar='GROUPS', default=None)
    parser.add_argument('-ds', '--delete_shares', nargs='*', help='Share names to be deleted e.g., -ds share1 share2', metavar='SHARES', default=None)
    parser.add_argument('-dup', '--delete_user_prename', help='Prename to delete user', metavar='NAME', default=None)
    parser.add_argument('-dusi', '--delete_user_start_index', help='Start index to delete user', type=int, metavar='INDEX', default=1)
    parser.add_argument('-dut', '--delete_user_total', help='Total to delete user', type=int, metavar='NUM', default=512)
    parser.add_argument('-cup', '--check_user_prename', help='Prename to check user', metavar='NAME', default=None)
    parser.add_argument('-cusi', '--check_user_start_index', help='Start index to check user', type=int, metavar='INDEX', default=1)
    parser.add_argument('-cut', '--check_user_total', help='Total to check user', type=int, metavar='NUM', default=512)
    parser.add_argument('-dgp', '--delete_group_prename', help='Prename to delete group', metavar='NAME', default=None)
    parser.add_argument('-dgsi', '--delete_group_start_index', help='Start index to delete group', type=int, metavar='INDEX', default=1)
    parser.add_argument('-dgt', '--delete_group_total', help='Total to delete group', type=int, metavar='NUM', default=512)

    sys.exit(UserGroup(parser.parse_args()).main())
