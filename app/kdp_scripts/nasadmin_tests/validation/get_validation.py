# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/validation - 200
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party
from deepdiff import DeepDiff


class GetValidation(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Fetch validation information'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5334'

    def test(self):
        resp = self.nasadmin.get_validation_info()
        local_users = self.ssh_client.get_local_users()
        local_usernames = set([unicode(u[0]) for u in local_users])
        diff = DeepDiff(set(resp['forbiddenUsernames']), local_usernames)
        if 'set_item_added' in diff:
            self.log.warning('forbiddenUsernames has no items for {}'.format(diff['set_item_added']))
        assert 'set_item_removed' not in diff,\
            "{} of forbiddenUsernames are not found in local".format(diff['set_item_removed'])


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get validation test ***
        """)

    test = GetValidation(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
