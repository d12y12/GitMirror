#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from os.path import exists, join
from .minisetting import Setting


def get_version(setting: Setting = None):
    setting = setting if setting else Setting()
    version = ""
    with open(setting['VERSION'], "r", encoding='utf8') as version_f:
        version = version_f.read().strip()
    return version


def get_token(setting: Setting = None, token_type=''):
    if not token_type or token_type.upper() not in ['GITHUB', 'GITEE']:
        return ()
    setting = setting if setting else Setting()
    key = token_type.upper() + '_TOKEN'
    if exists(setting[key]):
        token = ()
        with open(setting[key], "r", encoding='utf8') as token_f:
            token = token_f.read().strip().split(':')
        return (token[0], token[1]) if len(token) == 2 else ()
    return ()


def set_logger(setting: Setting, log_enable=True, log_level='DEBUG', log_file=None, log_dir=''):
    setting['LOG_ENABLED'] = log_enable
    setting['LOG_LEVEL'] = log_level
    setting['LOG_FILE'] = log_file
    if log_dir:
        setting['LOG_DIR'] = log_dir


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
