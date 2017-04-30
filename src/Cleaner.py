from __future__ import division
import logging

def zero_coocurence_count(db, now_category_for_parallel_execution):
    logging.info('['+now_category_for_parallel_execution+'] Reset coocurence counts for instances/patterns')
    instances = db['promoted_instances'].find()
    patterns = db['patterns'].find()

    for instance in instances:
        if instance['category_name'] != now_category_for_parallel_execution:
            continue
        db['promoted_instances'].update({'_id': instance['_id']},
                                        {'$set': {'count_in_text': 0}})

    # Here is a parallel shit
    check_category_id_for_parallel = -100
    categories = db['ontology'].find()
    for category in categories:
        if category['category_name'] == now_category_for_parallel_execution:
            check_category_id_for_parallel = category['_id']
            break
    categories.close()

    for pattern in patterns:
        if pattern['extracted_category_id'] != check_category_id_for_parallel:
            continue
        db['patterns'].update({'_id': pattern['_id']},
                              {'$set': {'coocurence_count': 0}})