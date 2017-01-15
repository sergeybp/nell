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

def extract_instances(db, iteration, useMorph):
    # iterate throw sentences, that contains categories
    # try to find patterns in this sentences
    logging.info("Begin instances extracting")
    category_pattern_dict.clear()
    categories = db['indexes'].find()
    tmpCats = list()
    for category in categories:
        tmpItem = dict()
        tmpItem['category_name'] = category['category_name']
        tmpItem['sentences_id'] = category['sentences_id']
        tmpItem['_id'] = category['_id']
        tmpCats.append(tmpItem)
    for cat in tmpCats:
        for sentence_id in cat['sentences_id']:
            sentence = db['sentences'].find_one({'_id': sentence_id})
            patterns = db['patterns'].find({'used': True})
            for pattern in patterns:
                if not (pattern['extracted_category_id'] == -1 or pattern['extracted_category_id'] == cat['_id']):
                    continue
                pattern_words_list = nltk.word_tokenize(pattern['string'])
                if ')' in pattern_words_list:
                    pattern_words_list.remove(')')
                arg1_pos, arg2_pos = check_if_pattern_exists_in_sentence(sentence, pattern_words_list)
                if arg2_pos is not None:
                    if arg2_pos >= len(sentence['words']) :
                        print('--' + sentence['string']+'   --  '+pattern['string'])
                if arg1_pos is not None and arg2_pos is not None and arg2_pos < len(sentence['words']):
                    arg1 = sentence['words'][arg1_pos]
                    arg2 = sentence['words'][arg2_pos]

                    if arg1['lexem'] == cat['category_name'] or \
                                    arg2['lexem'] == cat['category_name']:
                        if arg2['lexem'] == cat['category_name']:
                            (arg1, arg2) = (arg2, arg1)
                    else:
                        continue


                    flag = False
                    if not useMorph:
                        flag = True
                    if(check_words_for_pattern(arg1, arg2, pattern)):
                        flag = True
                    if flag:
                        item = db['promoted_instances'].find({'category_name': cat['category_name'],
                                                              'lexem': arg2['lexem']})
                        if item.count() > 0:
                            item = db['promoted_instances'].find_one({'category_name': cat['category_name'],
                                                                      'lexem': arg2['lexem']})
                            count_in_text = item['count_in_text']
                            if count_in_text == 0 or count_in_text is None:
                                count_in_text = 1
                            else:
                                count_in_text += 1
                            db['promoted_instances'].update({'_id': item['_id']},
                                                            {'$set': {'count_in_text': count_in_text}})
                            logging.info(
                                'Found excisting instance [%s] for category [%s], with pattern [%s] and [%d] coocurences' % \
                                (arg2['lexem'], cat['category_name'], pattern['string'], count_in_text))

                        else:
                            promoted_instance = dict()
                            promoted_instance['_id'] = db['promoted_instances'].find().count() + 1
                            promoted_instance['lexem'] = arg2['lexem']
                            promoted_instance['category_name'] = cat['category_name']
                            promoted_instance['used'] = False
                            promoted_instance['precision'] = 0
                            promoted_instance['extracted_pattern_id'] = pattern['_id']
                            promoted_instance['count_in_text'] = 1
                            promoted_instance['iteration_added'] = list()
                            promoted_instance['iteration_added'].append(iteration)
                            promoted_instance['iteration_deleted'] = list()

                            db['promoted_instances'].insert(promoted_instance)
                            logging.info("Found new promoted instance [%s] for category [%s], with pattern [%s]" % \
                                         (promoted_instance['lexem'], cat['category_name'], pattern['string']))
    categories.close()
    return


def evaluate_instances(db, treshold, iteration,ins_ngrams, MODE, dict_length):
    logging.info('Begin instances evaluating')
    promoted_instances = db['promoted_instances'].find()
    for instance in promoted_instances:
        if instance['extracted_pattern_id'] != -1:
            if instance['count_in_text'] == 0:
                continue
            if MODE == 1 :
                try:
                    precision = instance['count_in_text'] / ins_ngrams[instance['lexem'].lower()]
                except:
                    logging.error('Cannot find words %s in ngrams dictionary for instances' % instance['lexem'])
                    precision = 0
            if MODE == 2 :
                if db['ngrams_instances'].find({'lexem' : instance['lexem'].lower()}).count() > 0:
                    precision = instance['count_in_text'] / db['ngrams_instances'].find_one({'lexem' : instance['lexem'].lower()})['count']
                else :
                    logging.error('Cannot find words %s in ngrams dictionary for instances' % instance['lexem'])
                    precision = 0
            if MODE == 3:
                flag = False
                counter = 0
                for i in range(dict_length):
                    x = load_dictionary('ngrams_dictionary_for_instances' + str(i) + '.pkl')
                    try:
                        precision = instance['count_in_text'] / x[instance['lexem'].lower()]
                        flag = True
                    except:
                        counter += 1
                if counter == dict_length:
                    logging.error('Cannot find words %s in ngrams dictionary for instances' % instance['lexem'])
                    precision = 0
            logging.info("Precision for promoted instance [%s] for category [%s] updated from [%s] to [%s]" % \
                         (instance['lexem'],
                          instance['category_name'],
                          str(instance['precision']),
                          str(precision)))
            db['promoted_instances'].update({'_id': instance['_id']},
                                            {'$set': {'precision': precision}})

    # for each category we want to have n = 0..20 (will select later) numbers of promoted instances
    # at each iteration we calculate first 20 by precision
    # all that will be out of 20 but was at list earlier will be deleted
    tmpCats = list()
    categories = db['ontology'].find()
    for category in categories:
        tmpItem = dict()
        tmpItem['category_name'] = category['category_name']
        tmpItem['max_instance_precision'] = category['max_instance_precision']
        tmpItem['_id'] = category['_id']
        tmpCats.append(tmpItem)
    for cat in tmpCats:
        treshold = db['ontology'].find_one({'_id': cat['_id']})['max_instance_precision']
        promoted_instances_for_category = db['promoted_instances'].find({
            'category_name': cat['category_name']}).sort('precision', pymongo.DESCENDING)

        new_instances = 0
        deleted_instances = 0
        stayed_instances = 0
        for promoted_instance in promoted_instances_for_category:
            if promoted_instance['extracted_pattern_id'] == -1:
                stayed_instances += 1
                continue
            # first [n] NOT INITIAL instances must be added
            if promoted_instance['precision'] >= treshold:
                if promoted_instance['used']:
                    logging.info("Promoted instance [%s] stayed for category [%s] with precision [%s]" % \
                                 (promoted_instance['lexem'],
                                  promoted_instance['category_name'],
                                  str(promoted_instance['precision'])))
                    stayed_instances += 1
                else:
                    logging.info("Promoted instance [%s] added for category [%s] with precision [%s]" % \
                                 (promoted_instance['lexem'],
                                  promoted_instance['category_name'],
                                  str(promoted_instance['precision'])))
                    new_instances += 1
                    try:
                        iteration_added = promoted_instance['iteration_added']
                    except:
                        iteration_added = list()
                    iteration_added.append(iteration)
                    db['promoted_instances'].update({'_id': promoted_instance['_id']},
                                                    {'$set': {'used': True,
                                                              'iteration_added': iteration_added}})
                if cat['max_instance_precision'] == 0.0:
                    db['ontology'].update({'_id': cat['_id']},
                                          {'$set': {'max_instance_precision': promoted_instance['precision']}})
                logging.info('Updated category [%s] precision to [%.2f]' % (
                cat['category_name'], promoted_instance['precision']))

            # other instances must be deleted if they are not in first [n]
            else:
                if promoted_instance['used']:
                    logging.info("Promoted instance [%s] deleted for category [%s] with precision [%s]" % \
                                 (promoted_instance['lexem'],
                                  promoted_instance['category_name'],
                                  str(promoted_instance['precision'])))
                    deleted_instances += 1
                    try:
                        iteration_deleted = promoted_instance['iteration_added']
                    except:
                        iteration_deleted = list()
                    iteration_deleted.append(iteration)
                    db['promoted_instances'].update({'_id': promoted_instance['_id']},
                                                    {'$set': {'used': False,
                                                              'iteration_deleted': iteration_deleted}})

        logging.info("Add [%s] new instances, delete [%s], stayed [%d] instances for category [%s]" % \
                     (str(new_instances), str(deleted_instances), stayed_instances, cat['category_name']))
    categories.close()
    return

def check_if_pattern_exists_in_sentence(sentence, pattern_words_list):
    # check if pattern is in the sentence and return arg1/arg2 positions
    # FIXME now look into only one-word arguments, need to extend
    pattern_words_list.remove('arg1')
    pattern_words_list.remove('arg2')
    arg1_pos, arg2_pos = None, None

    for i in range(0, (len(sentence['words']) - len(pattern_words_list)) + 1):
        flag = True
        for j in range(0, len(pattern_words_list)):
            if sentence['words'][i]['original'] != pattern_words_list[j]:
                flag = False
                break
            i += 1
        if not flag:
            continue

        arg1_pos = i - len(pattern_words_list) - 1
        arg2_pos = arg1_pos + len(pattern_words_list) + 1
        break

    return (arg1_pos, arg2_pos)

def check_words_for_pattern(arg1, arg2, pattern):
    # check if arguments parameters are the same as in pattern
    try:
        if arg1['case'] == pattern['arg1']['case'] and \
                (arg1['number'] == pattern['arg1']['num'] or pattern['arg1']['num'] == 'all') and \
                        arg1['pos'].lower() == pattern['arg1']['pos'].lower() and \
                        arg2['case'] == pattern['arg2']['case'] and \
                (arg2['number'] == pattern['arg2']['num'] or pattern['arg2']['num'] == 'all') and \
                        arg2['pos'].lower() == pattern['arg2']['pos'].lower():
            return True
    except:
        pass
    return False