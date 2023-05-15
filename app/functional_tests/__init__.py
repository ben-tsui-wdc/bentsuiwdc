import glob
import os
from os.path import dirname, basename, isfile
from platform_libraries import common_utils


log = common_utils.create_logger(root_log=os.path.dirname(__file__).split('/')[-1])

modules = glob.glob(dirname(__file__)+"/*.py")
test_module_list = [ basename(f)[:-3] for f in modules if isfile(f) and '__init__' not in f]

test_class_list = [] 
for test_item in test_module_list:
    try:
        # import modules dynamically
        test_module = __import__(test_item, globals(), locals(), ['dummy'], -1)
        # get class from module
        test_class_list.append(getattr(test_module, test_item))
    except Exception as e:
        log.warn('Can not import {}'.format(test_item))
        print e