# -*- coding: utf-8 -*-
""" Implementation of MTBF feature.
"""

# std modules
import random


def gen_total_number(testcases, random_num):
    if isinstance(random_num, int):
        return random_num
    elif isinstance(random_num, tuple):
        return random.randint(*random_num)
    # "all"
    return len(testcases)

def choice_generator(testcases, random_num):
    total_number = gen_total_number(testcases, random_num)
    for idx in xrange(total_number):
        yield random.choice(testcases)

def unique_choice_generator(testcases, random_num):
    # Estimate testcases length.
    unique_list = []
    for ts in testcases:
        if ts not in unique_list:
            unique_list.append(ts)
    max_num = len(unique_list)
    # Unique choice.
    total_number = gen_total_number(testcases, random_num)
    if total_number > max_num:
        total_number = max_num
    run_tests = []
    for idx in xrange(total_number):
        testcase = random.choice(testcases)
        while testcase in run_tests:
            testcase = random.choice(testcases)
        run_tests.append(testcase)
        yield testcase

def gen_testcases(generator):
    return [ts for ts in generator]

def group_generator(testcases, original_source_testcases, exec_group):
    for group in exec_group.split():
        index_point = random.randint(0, len(testcases))
        for idx in eval(group):
            print "########## group: {}".format(idx)
            print original_source_testcases[idx]
            testcases.insert(index_point, original_source_testcases[idx])
            index_point = random.randint(index_point+1, len(testcases))
    return testcases