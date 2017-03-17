from __future__ import division
import logging

def zero_coocurence_count(db):
    logging.info('Reset coocurence counts for instances/patterns')
    instances = db['promoted_instances'].find()
    patterns = db['patterns'].find()

    for instance in instances:
        db['promoted_instances'].update({'_id': instance['_id']},
                                        {'$set': {'count_in_text': 0}})

    for pattern in patterns:
        db['patterns'].update({'_id': pattern['_id']},
                              {'$set': {'coocurence_count': 0}})