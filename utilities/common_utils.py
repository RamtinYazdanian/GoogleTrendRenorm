# coding=utf-8
import os
import errno

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def invert_dict(d):
    return {d[k]: k for k in d}