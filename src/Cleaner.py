import pandas as pd
from pymystem3 import Mystem
import nltk
import string
import pymorphy2
import logging
import pymongo
import pickle

mystem = Mystem()
punctuation = string.punctuation

morph = pymorphy2.MorphAnalyzer()
category_pattern_dict = dict()
INF = 100 * 100 * 100

MODE = 1

def zero_coocurence_count(db):
    logging.info('Reser coocurence counts for instances/patterns')
    instances = db['promoted_instances'].find()
    patterns = db['patterns'].find()

    for instance in instances:
        db['promoted_instances'].update({'_id': instance['_id']},
                                        {'$set': {'count_in_text': 0}})

    for pattern in patterns:
        db['patterns'].update({'_id': pattern['_id']},
                              {'$set': {'coocurence_count': 0}})