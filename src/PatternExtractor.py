from __future__ import division
import nltk
import logging
import pymongo
import pickle


tmp_count_dict = dict()

def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj

def extract_patterns(db, iteration):
    logging.info('Begin pattern extraction')
    categories = db['indexes'].find()
    tmp_list_categories = list()
    for category in categories:
        tmp_item = dict()
        tmp_item['category_name'] = category['category_name']
        tmp_item['sentences_id'] = category['sentences_id']
        tmp_item['_id'] = category['_id']
        tmp_list_categories.append(tmp_item)
    for now_category in tmp_list_categories:
        tmp_count_dict = dict()
        for sentence_id in now_category['sentences_id']:
            instances = db['promoted_instances'].find({'category_name': now_category['category_name'],
                                                       'used': True})
            sentence = db['sentences'].find_one({'_id': sentence_id})
            for instance in instances:
                if check_word_in_sentence(sentence, instance['lexem']) != -1:
                    arg1_pos = check_word_in_sentence(sentence, now_category['category_name'])
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
                                            'extracted_category_id': now_category['_id'],
                                            'arg1': promoted_pattern['arg1'],
                                            'arg2': promoted_pattern['arg2']}).count() > 0:

                        found_pattern = db['patterns'].find_one({'string': pattern_string,
                                                                 'extracted_category_id': now_category['_id'],
                                                                 'arg1': promoted_pattern['arg1'],
                                                                 'arg2': promoted_pattern['arg2']})
                        coocurence_count = found_pattern['coocurence_count']
                        coocurence_count += 1
                        db['patterns'].update({'_id': found_pattern['_id']},
                                              {'$set': {'coocurence_count': coocurence_count}})

                        logging.info(
                            'Updating excisting pattern [%s] for category [%s] found for instance [%s] with [%d] coocurences' % \
                            (found_pattern['string'], category['category_name'], instance['lexem'],
                             coocurence_count))

                    elif db['patterns'].find({'string': pattern_string,
                                              'extracted_category_id': -1}).count() > 0:
                        logging.info('Found initial pattern [%s], skipping' % pattern_string)
                        continue
                    else:

                        really_need_to_promote = False
                        x = 1
                        try:
                            x = tmp_count_dict[pattern_string]
                            x += 1
                            tmp_count_dict[pattern_string] = x
                            if x >= 2:
                                really_need_to_promote = True
                        except:
                            tmp_count_dict[pattern_string] = 1

                        if not really_need_to_promote:
                            continue

                        promoted_pattern['_id'] = db['patterns'].find().count() + 1
                        promoted_pattern['iteration_added'] = [iteration]
                        promoted_pattern['iteration_deleted'] = list()
                        promoted_pattern['used'] = False
                        promoted_pattern['extracted_category_id'] = now_category['_id']
                        promoted_pattern['coocurence_count'] = x
                        promoted_pattern['string'] = pattern_string
                        promoted_pattern['precision'] = 0

                        # FIXME think about this metrics later
                        promoted_pattern['true_detective'] = 0
                        promoted_pattern['false_detective'] = 0

                        # TODO think about the situation, when the pattern found with different 'num' field in words,
                        # TODO but the same conditions for everything else

                        db['patterns'].insert(promoted_pattern)
                        logging.info('Found new pattern [%s] for category [%s] found for instance [%s] with [%d] coocurences' % \
                                     (promoted_pattern['string'], now_category['category_name'], instance['lexem'], promoted_pattern['coocurence_count']))
                        break
    categories.close()
    return


def evaluate_patterns(db, fixed_threshold_between_zero_and_one ,threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, patterns_ngrams_dictionary, ngrams_dictionary_mode, ngrams_dictionaries_count, now_category):
    logging.info('Begin patterns evaluation')
    patterns = db['patterns'].find()
    tmp_list_patterns = list()
    for pattern in patterns:
        tmp_item = dict()
        tmp_item['extracted_category_id'] = pattern['extracted_category_id']
        tmp_item['string'] = pattern['string']
        tmp_item['coocurence_count'] = pattern['coocurence_count']
        tmp_item['_id'] = pattern['_id']
        tmp_list_patterns.append(tmp_item)
    for now_pattern in tmp_list_patterns:
        if now_pattern['extracted_category_id'] == -1:
            continue
        pattern_string = now_pattern['string']
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
        if now_pattern['coocurence_count'] < 3:
            continue
        if ngrams_dictionary_mode == 1:
            try:
                precision = now_pattern['coocurence_count'] / patterns_ngrams_dictionary[pattern_string]
            except:
                logging.error('Cannot find words %s in ngrams_dict' % pattern_string)
                precision = 0
        if ngrams_dictionary_mode == 2:
            counter = 0
            for i in range(ngrams_dictionaries_count):
                x = load_dictionary('ngrams_dictionary_for_patterns.' + now_category + '.' + str(i) + '.pkl')
                try:
                    precision = now_pattern['coocurence_count'] / x[pattern_string]
                except:
                    counter += 1
            if counter == ngrams_dictionaries_count:
                logging.error('Cannot find words %s in ngrams_dict' % pattern_string)
                precision = 0
        if precision > 1:
            precision = 1.0
        db['patterns'].update({'_id': now_pattern['_id']},
                              {'$set': {'precision': precision}})

    categories = db['ontology'].find()
    tmp_list_categories = list()
    for category in categories:
        tmp_item = dict()
        tmp_item['category_name'] = category['category_name']
        tmp_item['max_pattern_precision'] = category['max_pattern_precision']
        tmp_item['_id'] = category['_id']
        tmp_list_categories.append(tmp_item)
    for now_category in tmp_list_categories:
        if(threshold_mode == 3):
            treshold = db['ontology'].find_one({'_id': now_category['_id']})['max_pattern_precision']
            treshold = treshold * threshold_k_factor
        elif(threshold_mode == 2):
            treshold = fixed_threshold_between_zero_and_one
        else:
            treshold = threshold_fixed_n
        promoted_patterns_for_category = db['patterns'].find({
            'extracted_category_id': now_category['_id']}).sort('precision', pymongo.DESCENDING)
        new_patterns, deleted_patterns, stayed_patterns = 0, 0, 0

        if threshold_mode != 1:
            evaluation_mode_fixed_value_threshold(promoted_patterns_for_category,treshold,now_category,stayed_patterns,new_patterns,iteration,db,deleted_patterns)
        else:
            evaluation_mode_fixed_size_threshold(promoted_patterns_for_category,treshold,category,stayed_patterns,new_patterns,iteration,db,deleted_patterns,now_category)
    categories.close()
    return

def evaluation_mode_fixed_size_threshold(promoted_patterns_for_category, treshold, category, stayed_patterns, new_patterns, iteration,db, deleted_patterns, now_category):
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
          (new_patterns, deleted_patterns, stayed_patterns, now_category['category_name']))

def evaluation_mode_fixed_value_threshold(promoted_patterns_for_category, treshold, now_category, stayed_patterns, new_patterns, iteration, db, deleted_patterns):
    for promoted_pattern in promoted_patterns_for_category:
        if promoted_pattern['extracted_category_id'] == -1:
            continue
        if promoted_pattern['precision'] >= treshold:
            if promoted_pattern['used']:
                logging.info("Promoted pattern [%s] stayed for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              now_category['category_name'],
                              str(promoted_pattern['precision'])))
                stayed_patterns += 1
            else:
                logging.info("Promoted pattern [%s] added for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              now_category['category_name'],
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

            if now_category['max_pattern_precision'] == 0.0:
                db['ontology'].update({'_id': now_category['_id']},
                                      {'$set': {'max_pattern_precision': promoted_pattern['precision']}})
                logging.info('Updated category [%s] precision to [%.2f]' % \
                             (now_category['category_name'], promoted_pattern['precision']))
        else:
            if promoted_pattern['used']:
                logging.info("Promoted instance [%s] deleted for category [%s] with precision [%s]" % \
                             (promoted_pattern['string'],
                              now_category['category_name'],
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
                 (new_patterns, deleted_patterns, stayed_patterns, now_category['category_name']))

def check_word_in_sentence(sentence, lexem):
    # help to find the word lexem in the sentence and return its position if it exists
    pos = 0
    for word in sentence['words']:
        if lexem == word['lexem']:
            return pos
        pos += 1
    return -1