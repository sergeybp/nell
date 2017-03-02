from __future__ import division
import threading
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


def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj

def extract_patterns(db, iteration, nowCategory):
    logging.info('Begin pattern extraction for category: ' + nowCategory['category_name'])
    cat = nowCategory
    for sentence_id in cat['sentences_id']:
        instances = db['promoted_instances'].find({'category_name': cat['category_name'],
                                                   'used': True})
        sentence = db['sentences'].find_one({'_id': sentence_id})
        for instance in instances:
            if check_word_in_sentence(sentence, instance['lexem']) != -1:
                arg1_pos = check_word_in_sentence(sentence, cat['category_name'])
                arg2_pos = check_word_in_sentence(sentence, instance['lexem'])

                if abs(arg1_pos - arg2_pos) >= 5:
                    # choose the patterns not more than 5 words im sum with arg1/arg2
                    continue

                # just because we have different types of patterns we need to check this conditions
                # to form the pattern string
                if arg1_pos < arg2_pos:
                    pattern_string = 'arg1 '
                    for i in range(arg1_pos + 1, arg2_pos):
                        pattern_string += sentence['words'][i]['original']
                        pattern_string += ' '
                    pattern_string += 'arg2'
                else:
                    pattern_string = 'arg2 '
                    for i in range(arg2_pos + 1, arg1_pos):
                        pattern_string += sentence['words'][i]['original']
                        pattern_string += ' '
                    pattern_string += 'arg1'

                if '(' in pattern_string and ')' not in pattern_string:
                    pattern_string += ' )'

                if pattern_string == 'arg1 arg2' or pattern_string == 'arg2 arg1':
                    continue

                promoted_pattern = dict()
                promoted_pattern['arg1'] = dict()
                promoted_pattern['arg1']['num'] = sentence['words'][arg1_pos]['number']
                promoted_pattern['arg1']['case'] = sentence['words'][arg1_pos]['case']
                promoted_pattern['arg1']['pos'] = sentence['words'][arg1_pos]['pos']

                promoted_pattern['arg2'] = dict()
                promoted_pattern['arg2']['num'] = sentence['words'][arg2_pos]['number']
                promoted_pattern['arg2']['case'] = sentence['words'][arg2_pos]['case']
                promoted_pattern['arg2']['pos'] = sentence['words'][arg2_pos]['pos']

                if db['patterns'].find({'string': pattern_string,
                                        'extracted_category_id': cat['_id'],
                                        'arg1': promoted_pattern['arg1'],
                                        'arg2': promoted_pattern['arg2']}).count() > 0:

                    found_pattern = db['patterns'].find_one({'string': pattern_string,
                                                             'extracted_category_id': cat['_id'],
                                                             'arg1': promoted_pattern['arg1'],
                                                             'arg2': promoted_pattern['arg2']})
                    coocurence_count = found_pattern['coocurence_count']
                    coocurence_count += 1
                    db['patterns'].update({'_id': found_pattern['_id']},
                                          {'$set': {'coocurence_count': coocurence_count}})

                    logging.info(
                        'Updating excisting pattern [%s] for category [%s] found for instance [%s] with [%d] coocurences' % \
                        (found_pattern['string'], cat['category_name'], instance['lexem'],
                         found_pattern['coocurence_count']))

                elif db['patterns'].find({'string': pattern_string,
                                          'extracted_category_id': -1}).count() > 0:
                    logging.info('Found initial pattern [%s], skipping' % pattern_string)
                    continue
                else:
                    promoted_pattern['iteration_added'] = [iteration]
                    promoted_pattern['iteration_deleted'] = list()
                    promoted_pattern['used'] = False
                    promoted_pattern['extracted_category_id'] = cat['_id']
                    promoted_pattern['coocurence_count'] = 1
                    promoted_pattern['string'] = pattern_string
                    promoted_pattern['precision'] = 0

                    # FIXME think about this metrics later
                    promoted_pattern['true_detective'] = 0
                    promoted_pattern['false_detective'] = 0

                    # TODO think about the situation, when the pattern found with different 'num' field in words,
                    # TODO but the same conditions for everything else

                    db['patterns'].insert(promoted_pattern)
                    logging.info('Found new pattern [%s] for category [%s] found for instance [%s]' % \
                             (promoted_pattern['string'], cat['category_name'], instance['lexem']))

                    break
    return


def evaluate_patterns(db, tT ,tMode, tK, tN, iteration, tmpDict, MODE, dict_length, nowCategory):
    logging.info('Begin patterns evaluation fro category: ' + nowCategory['category_name'])
    patterns = db['patterns'].find()
    tmpPats = list()
    for pattern in patterns:

        tmpItem = dict()
        tmpItem['extracted_category_id'] = pattern['extracted_category_id']
        tmpItem['string'] = pattern['string']
        tmpItem['coocurence_count'] = pattern['coocurence_count']
        tmpItem['_id'] = pattern['_id']
        tmpPats.append(tmpItem)
    for pat in tmpPats:
        if pat['extracted_category_id'] == -1:
            continue
        pattern_string = pat['string']
        pattern_tokens = nltk.word_tokenize(pattern_string)
        pattern_tokens.remove('arg1')
        pattern_tokens.remove('arg2')
        if ')' in pattern_tokens:
            pattern_tokens.remove(')')
        pattern_string = ''
        for token in pattern_tokens:
            pattern_string += token.lower()
            pattern_string += ' '
        pattern_string = pattern_string[:-1]
        #NEW CHECK!!
        if pat['coocurence_count'] <= 15:
            continue
        if MODE == 1:
            try:
                precision = pat['coocurence_count'] / tmpDict[pattern_string]
            except:
                logging.error('Cannot find words %s in ngrams_dict' % pattern_string)
                precision = 0
        if MODE == 2:
            if db['ngrams_patterns'].find({'lexem' : pattern_string}).count() > 0 :
                precision = pat['coocurence_count'] / db['ngrams_patterns'].find_one({'lexem' : pattern_string})['count']
            else:
                logging.error('Cannot find words %s in ngrams_dict' % pattern_string)
                precision = 0
        if MODE == 3:
            counter = 0
            for i in range(dict_length):
                x = load_dictionary('ngrams_dictionary_for_patterns.' + str(i) + '.pkl')
                try:
                    precision = pat['coocurence_count'] / x[pattern_string]
                except:
                    counter += 1
            if counter == dict_length:
                logging.error('Cannot find words %s in ngrams_dict' % pattern_string)
                precision = 0
        if precision > 1:
            precision = 1.0
        db['patterns'].update({'_id': pat['_id']},
                              {'$set': {'precision': precision}})

    cat = nowCategory
    if(tMode == 3):
        treshold = db['ontology'].find_one({'_id': cat['_id']})['max_pattern_precision']
        treshold = treshold * tK
    elif(tMode == 2):
        treshold = tT
    else:
        treshold = tN
    promoted_patterns_for_category = db['patterns'].find({
        'extracted_category_id': cat['_id']}).sort('precision', pymongo.DESCENDING)
    new_patterns, deleted_patterns, stayed_patterns = 0, 0, 0

    if tMode != 1:
        evaluationModeTwoAndThree(promoted_patterns_for_category,treshold,cat,stayed_patterns,new_patterns,iteration,db,deleted_patterns)
    else:
        evaluationModeOne(promoted_patterns_for_category,treshold,cat,stayed_patterns,new_patterns,iteration,db,deleted_patterns,cat)
    return

def evaluationModeOne(promoted_patterns_for_category, treshold, category, stayed_patterns, new_patterns, iteration,db, deleted_patterns, cat):
    size = treshold
    for promoted_pattern in promoted_patterns_for_category:
        if promoted_pattern['extracted_category_id'] == -1:
            continue
        if size > 0:
            if promoted_pattern['used']:
                logging.info("Promoted pattern [%s] stayed for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              category['category_name'],
                              str(promoted_pattern['precision'])))
                stayed_patterns += 1
            else:
                logging.info("Promoted pattern [%s] added for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              category['category_name'],
                              str(promoted_pattern['precision'])))
                new_patterns += 1
                try:
                    iteration_added = promoted_pattern['iteration_added']
                except:
                    iteration_added = list()
                iteration_added.append(iteration)
                db['patterns'].update({'_id': promoted_pattern['_id']},
                                      {'$set': {'used': True,
                                                'iteration_added': iteration_added}})
            size -= 1
        else:
            if promoted_pattern['used']:
                logging.info("Promoted instance [%s] deleted for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              category['category_name'],
                              str(promoted_pattern['precision'])))
                deleted_patterns += 1
                try:
                    iteration_deleted = promoted_pattern['iteration_deleted']
                except:
                    iteration_deleted = list()
                db['patterns'].update({'_id': promoted_pattern['_id']},
                                      {'$set': {'used': False,
                                                'iteration_deleted': iteration_deleted}})
    logging.info("Add [%d] new patterns, delete [%d], stayed [%d] patterns for category [%s]" % \
          (new_patterns, deleted_patterns, stayed_patterns, cat['category_name']))

def evaluationModeTwoAndThree(promoted_patterns_for_category, treshold, cat, stayed_patterns, new_patterns, iteration, db, deleted_patterns):
    for promoted_pattern in promoted_patterns_for_category:
        if promoted_pattern['extracted_category_id'] == -1:
            continue
        if promoted_pattern['precision'] >= treshold:
            if promoted_pattern['used']:
                logging.info("Promoted pattern [%s] stayed for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              cat['category_name'],
                              str(promoted_pattern['precision'])))
                stayed_patterns += 1
            else:
                logging.info("Promoted pattern [%s] added for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              cat['category_name'],
                              str(promoted_pattern['precision'])))
                new_patterns += 1
                try:
                    iteration_added = promoted_pattern['iteration_added']
                except:
                    iteration_added = list()
                iteration_added.append(iteration)
                db['patterns'].update({'_id': promoted_pattern['_id']},
                                      {'$set': {'used': True,
                                                'iteration_added': iteration_added}})

            if cat['max_pattern_precision'] == 0.0:
                db['ontology'].update({'_id': cat['_id']},
                                      {'$set': {'max_pattern_precision': promoted_pattern['precision']}})
                logging.info('Updated category [%s] precision to [%.2f]' % \
                             (cat['category_name'], promoted_pattern['precision']))
        else:
            if promoted_pattern['used']:
                logging.info("Promoted instance [%s] deleted for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              cat['category_name'],
                              str(promoted_pattern['precision'])))
                deleted_patterns += 1
                try:
                    iteration_deleted = promoted_pattern['iteration_deleted']
                except:
                    iteration_deleted = list()
                db['patterns'].update({'_id': promoted_pattern['_id']},
                                      {'$set': {'used': False,
                                                'iteration_deleted': iteration_deleted}})
    logging.info("Add [%d] new patterns, delete [%d], stayed [%d] patterns for category [%s]" % \
                 (new_patterns, deleted_patterns, stayed_patterns, cat['category_name']))

def check_word_in_sentence(sentence, lexem):
    # help to find the word lexem in the sentence and return its position if it exists
    pos = 0
    for word in sentence['words']:
        if lexem == word['lexem']:
            return pos
        pos += 1
    return -1