from __future__ import division
import nltk
import logging
import pymongo
import pickle

category_pattern_dict = dict()
tmp_count_dict = dict()

def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj


def extract_instances(db, iteration, use_morph):
    logging.info("Begin instances extracting")
    category_pattern_dict.clear()
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
            sentence = db['sentences'].find_one({'_id': sentence_id})
            patterns = db['patterns'].find({'used': True})
            for pattern in patterns:
                if not (pattern['extracted_category_id'] == -1 or pattern['extracted_category_id'] == now_category['_id']):
                    continue
                pattern_words_list = nltk.word_tokenize(pattern['string'])
                if ')' in pattern_words_list:
                    pattern_words_list.remove(')')
                arg1_pos, arg2_pos = check_if_pattern_exists_in_sentence(sentence, pattern_words_list)

                if arg2_pos is not None:
                    if arg2_pos >= len(sentence['words']):
                        logging.info('Pattern [' + pattern['string'] + '] is too long for sentence [' + sentence['string'] + '].')

                if arg1_pos is not None and arg2_pos is not None and arg2_pos < len(sentence['words']):
                    arg1 = sentence['words'][arg1_pos]
                    arg2 = sentence['words'][arg2_pos]

                    if arg1['lexem'] == now_category['category_name'] or \
                                    arg2['lexem'] == now_category['category_name']:
                        if arg2['lexem'] == now_category['category_name']:
                            (arg1, arg2) = (arg2, arg1)
                            (arg1_pos, arg2_pos) = (arg2_pos, arg1_pos)
                    else:
                        continue

                    #word next arg2 for complex instances
                    next_word= None
                    if arg2_pos-1 >= 0:
                        next_word = sentence['words'][arg2_pos-1]

                    need_promote = False
                    if not use_morph:
                        need_promote = True
                        next_word = None

                    if (check_words_for_pattern(arg1, arg2, pattern)):
                        need_promote = True
                        next_word = None

                    additional_word = None
                    if not need_promote and next_word is not None:
                        if check_words_for_complex_instance(arg1, arg2, next_word, pattern):
                            need_promote = True
                            additional_word = arg2
                            arg2 = next_word

                    if need_promote:
                        item = db['promoted_instances'].find({'category_name': now_category['category_name'],
                                                              'lexem': arg2['lexem']})
                        if item.count() > 0:
                            item = db['promoted_instances'].find_one({'category_name': now_category['category_name'],
                                                                      'lexem': arg2['lexem']})
                            count_in_text = item['count_in_text']
                            if count_in_text == 0 or count_in_text is None:
                                count_in_text = 1
                            else:
                                count_in_text += 1

                            db['promoted_instances'].update({'_id': item['_id']},
                                                            {'$set': {'count_in_text': count_in_text}})
                            if not additional_word is None:
                                try:
                                    ad_words = item['ad_words']
                                except:
                                    ad_words = list()
                                if not additional_word in ad_words:
                                    ad_words.append(additional_word)
                                db['promoted_instances'].update({'_id': item['_id']},
                                                                {'$set': {'ad_words': ad_words}})

                            logging.info(
                                'Found excisting instance [%s] for category [%s], with pattern [%s] and [%d] coocurences' % \
                                (arg2['lexem'], now_category['category_name'], pattern['string'], count_in_text))

                        else:
                            really_need_to_promote = False
                            x = 1
                            try:
                                x = tmp_count_dict[arg2['lexem']]
                                x += 1
                                tmp_count_dict[arg2['lexem']] = x
                                if x >= 2:
                                    really_need_to_promote = True
                            except:
                                tmp_count_dict[arg2['lexem']] = 1

                            if not really_need_to_promote:
                                continue

                            promoted_instance = dict()
                            promoted_instance['_id'] = db['promoted_instances'].find().count() + 1
                            promoted_instance['lexem'] = arg2['lexem']
                            promoted_instance['category_name'] = now_category['category_name']
                            promoted_instance['used'] = False
                            promoted_instance['precision'] = 0
                            promoted_instance['extracted_pattern_id'] = pattern['_id']
                            promoted_instance['count_in_text'] = x
                            promoted_instance['iteration_added'] = list()
                            promoted_instance['iteration_added'].append(iteration)
                            promoted_instance['iteration_deleted'] = list()
                            if additional_word is not None:
                                ad_words = list()
                                ad_words.append(additional_word)
                                promoted_instance['ad_words'] = ad_words
                            else:
                                promoted_instance['ad_words'] = list()

                            db['promoted_instances'].insert(promoted_instance)
                            logging.info("Found new promoted instance [%s] for category [%s], with pattern [%s]" % \
                                         (promoted_instance['lexem'], now_category['category_name'], pattern['string']))
    categories.close()
    return


def evaluate_instances(db, fixed_threshold_between_zero_and_one, threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, instances_ngrams_dictionary, ngrams_dictionary_mode, ngrams_dictionaries_count, now_category):
    logging.info('Begin instances evaluating')
    promoted_instances = db['promoted_instances'].find()
    for instance in promoted_instances:
        if instance['extracted_pattern_id'] != -1:
            if instance['count_in_text'] < 3:
                continue
            if ngrams_dictionary_mode == 1:
                try:
                    precision = instance['count_in_text'] / instances_ngrams_dictionary[instance['lexem'].lower()]
                except:
                    logging.error('Cannot find words %s in ngrams dictionary for instances' % instance['lexem'])
                    precision = 0
            if ngrams_dictionary_mode == 2:
                tmp_dictionaries_counter = 0
                for i in range(ngrams_dictionaries_count):
                    now_dictionary = load_dictionary('ngrams_dictionary_for_instances.' + now_category + '.' + str(i) + '.pkl')
                    try:
                        precision = instance['count_in_text'] / now_dictionary[instance['lexem'].lower()]
                    except:
                        tmp_dictionaries_counter += 1
                if tmp_dictionaries_counter == ngrams_dictionaries_count:
                    logging.error('Cannot find words %s in ngrams dictionary for instances' % instance['lexem'])
                    precision = 0
            logging.info("Precision for promoted instance [%s] for category [%s] updated from [%s] to [%s]" % \
                         (instance['lexem'],
                          instance['category_name'],
                          str(instance['precision']),
                          str(precision)))
            db['promoted_instances'].update({'_id': instance['_id']},
                                            {'$set': {'precision': precision}})

    tmp_list_categories = list()
    categories = db['ontology'].find()
    for category in categories:
        tmp_item = dict()
        tmp_item['category_name'] = category['category_name']
        tmp_item['max_instance_precision'] = category['max_instance_precision']
        tmp_item['_id'] = category['_id']
        tmp_list_categories.append(tmp_item)
    for now_category in tmp_list_categories:
        if (threshold_mode == 3):
            threshold = db['ontology'].find_one({'_id': now_category['_id']})['max_instance_precision']
            threshold = threshold * threshold_k_factor
        elif (threshold_mode == 2):
            threshold = fixed_threshold_between_zero_and_one
        else:
            threshold = threshold_fixed_n

        promoted_instances_for_category = db['promoted_instances'].find({
            'category_name': now_category['category_name']}).sort('precision', pymongo.DESCENDING)

        if threshold_mode != 1:
            evaluation_mode_fixed_value_threshold(promoted_instances_for_category, threshold, iteration, db, now_category)
        else:
            evaluation_mode_fixed_size_threshold(promoted_instances_for_category, threshold, iteration, db, now_category)
    categories.close()
    return


def evaluation_mode_fixed_size_threshold(promoted_instances_for_category, threshold, iteration, db, now_category):
    size = threshold
    new_instances = 0
    deleted_instances = 0
    stayed_instances = 0
    for promoted_instance in promoted_instances_for_category:
        if promoted_instance['extracted_pattern_id'] == -1:
            stayed_instances += 1
            continue
        if size > 0:
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
            size -= 1
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
                 (str(new_instances), str(deleted_instances), stayed_instances, now_category['category_name']))


def evaluation_mode_fixed_value_threshold(promoted_instances_for_category, threshold, iteration, db, now_category):
    new_instances = 0
    deleted_instances = 0
    stayed_instances = 0
    for promoted_instance in promoted_instances_for_category:
        if promoted_instance['extracted_pattern_id'] == -1:
            stayed_instances += 1
            continue
        if promoted_instance['precision'] >= threshold:
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
            if now_category['max_instance_precision'] == 0.0:
                db['ontology'].update({'_id': now_category['_id']},
                                      {'$set': {'max_instance_precision': promoted_instance['precision']}})
            logging.info('Updated category [%s] precision to [%.2f]' % (
                now_category['category_name'], promoted_instance['precision']))

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
                 (str(new_instances), str(deleted_instances), stayed_instances, now_category['category_name']))


def check_if_pattern_exists_in_sentence(sentence, pattern_words_list):
    # check if pattern is in the sentence and return arg1/arg2 positions
    # FIXME now look into only one-word arguments, need to extend
    pattern_words_list.remove('arg1')
    pattern_words_list.remove('arg2')
    arg1_pos, arg2_pos = None, None

    for i in range(0, (len(sentence['words']) - len(pattern_words_list)) + 1):
        need_promote = True
        for j in range(0, len(pattern_words_list)):
            if sentence['words'][i]['original'] != pattern_words_list[j]:
                need_promote = False
                break
            i += 1
        if not need_promote:
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

def check_words_for_complex_instance(arg1, arg2, next_word, pattern):
    pattern_words_list = nltk.word_tokenize(pattern['string'])
    if next_word['original'] == pattern_words_list[0]:
        return False
    try:
        if next_word['case'] == pattern['arg2']['case'] and \
                (next_word['number'] == pattern['arg2']['num'] or pattern['arg2']['num'] == 'all') and \
                        next_word['pos'].lower() == pattern['arg2']['pos'].lower() and \
                        arg1['case'] == pattern['arg1']['case'] and \
                (arg1['number'] == pattern['arg1']['num'] or pattern['arg1']['num'] == 'all') and \
                        arg1['pos'].lower() == pattern['arg1']['pos'].lower():
            if arg2['pos'].lower() == 'adjf':
                return True
            else :
                return False
    except:
        pass
    return False
