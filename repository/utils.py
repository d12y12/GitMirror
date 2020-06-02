#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from os.path import exists, join
from .minisetting import Setting


def get_version(setting: Setting = None):
    setting = setting if setting else Setting()
    return open(setting['VERSION'], "r").read().strip()


def get_github_token(setting: Setting = None):
    setting = setting if setting else Setting()
    if exists(setting['GITHUB_TOKEN']):
        token = open(setting['GITHUB_TOKEN'], "r").read().split(':')
        return (token[0], token[1]) if len(token) == 2 else ()
    return ()


def set_logger(setting: Setting, log_enable=True, log_level='DEBUG', log_file=None):
    setting['LOG_ENABLED'] = log_enable
    setting['LOG_LEVEL'] = log_level
    setting['LOG_FILE'] = log_file


def config_logging(setting=None):
    setting = setting if setting else Setting()
    logger = logging.getLogger()
    logger.setLevel(setting['LOG_LEVEL'])
    formatter = logging.Formatter(setting['LOG_FORMAT'])
    if setting['LOG_FILE']:
        log_file = logging.FileHandler(join(setting['LOG_DIR'], setting['LOG_FILE']))
        log_file.setFormatter(formatter)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    if setting['LOG_ENABLED']:
        if setting['LOG_FILE']:
            logger.addHandler(log_file)
        logger.addHandler(console)
    else:
        logger.addHandler(logging.NullHandler())

def get_logger(name, setting=None):
    return None