# -*-coding: utf-8 -*-
""" Tool set for assert actions.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# Assert tools

def assert_equal(value, expect, value_desc=None):
    if not value_desc:
        value_desc = 'Assert value'
    assert value == expect, \
        '{} is {} but expect it is {}'.format(value_desc, value, expect)

def assert_dict(value, expect):
    # Only compare the data pairs from expect.
    for k, v in expect.iteritems():
        if k in value:
            assert value[k] == expect[k], "{}: {} != {}".format(k, value[k], expect[k])

def assert_dict_with_value_type(value, expect):
    # Only compare the data type pairs from expect.
    for k, t in expect.iteritems():
        if k in value:
            assert isinstance(value[k], t), \
                "{}: {} is not type of {}, it is {}".format(k, value[k], expect[k], type(value[k]))

def assert_dict_key_only(value, expect_keys):
    # Only check the keys from expect.
    for k in expect_keys:
        assert k in value, "Cannot found key: {} in the dict".format(k)

# nasAdmin assert tools

def nsa_assert_user(cloud_user, cmp_user, localAccess=False, username="", description=""):
    """ Compare nasAdmin user with cloud user info
    """
    assert cmp_user['cloudID'] == cloud_user['user_id'], \
        "cloudID: {} != {}".format(cmp_user['cloudID'], cloud_user['user_id'])
    assert cmp_user['email'] == cloud_user['email'], \
        "email: {} != {}".format(cmp_user['email'], cloud_user['email'])
    assert cmp_user['firstName'] == cloud_user['user_metadata']['first_name'], \
        "firstName: {} != {}".format(cmp_user['firstName'], cloud_user['user_metadata']['first_name'])
    assert cmp_user['lastName'] == cloud_user['user_metadata']['last_name'], \
        "lastName: {} != {}".format(cmp_user['lastName'], cloud_user['user_metadata']['last_name'])
    assert cmp_user['localAccess'] == localAccess, "localAccess is not {}".format(localAccess)
    assert cmp_user['username'] == username, "username: {} != {}".format(cmp_user['username'], username)
    assert cmp_user['description'] == description, "description: {} != {}".format(cmp_user['description'], description)

def nsa_assert_user_by_dict(check_data_dict, cmp_user, ignore_field_names=None):
    """ Compare nasAdmin user with given "check_data_dict".
    """
    if not ignore_field_names: ignore_field_names = []
    for name in [n for n in check_data_dict if n not in ignore_field_names]:
        if name not in cmp_user:
            assert AssertionError('Key:{} not found in user info'.format(name))
        assert cmp_user[name] == check_data_dict[name], \
            "{}: {} != {}".format(name, cmp_user[name], check_data_dict[name])
