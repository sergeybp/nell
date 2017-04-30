import string

import logging
import nltk
import pymorphy2
from pymongo import MongoClient

db = None

morph = pymorphy2.MorphAnalyzer()
punctuation = string.punctuation


def connect_to_database():
    client = MongoClient('localhost', 27017)
    global db
    db = client['all']


def find_sub_pattern(db, pattern):
    words = nltk.word_tokenize(pattern['string'])
    found = False
    found_w = None
    old_w = None
    ontology = db['indexes'].find()
    categories = dict()
    for cat in ontology:
        categories[cat['_id']] = cat['category_name']
    if pattern['extracted_category_id'] == -1:
        return None
    for word in words:
        if not word == 'arg1' and not word == 'arg2':
            w = find_another_word(db, word, categories[pattern['extracted_category_id']])
            if not w is None:
                found = True
                found_w = w
                old_w = word
                break
    if found:
        for i in range(0, len(words)):
            if words[i] == 'arg2':
                words[i] = ''
                continue
            if words[i] == old_w:
                words[i] = 'arg2'
                continue
        words = cut_words(words)
        new_pat = ''
        for word in words:
            new_pat += word + ' '
        pattern['string'] = new_pat
        return pattern
    return None


def cut_words(words):
    res = list()
    cut = False
    for word in words:
        if word == 'arg1' or word == 'arg2':
            if not cut:
                cut = True
                res.append(word)
                continue
            else:
                res.append(word)
                return res
        if not word == '':
            res.append(word)


def find_another_word(db, word, cat):
    instances = db['promoted_instances'].find({'used':True, 'category_name':cat})
    if word in punctuation:
        return None
    p = morph.parse(word)
    lex = p[0].normal_form
    for instance in instances:
        if instance['lexem'] == lex and instance['category_name'] == cat:
            return instance
    return None


def filter_all_patterns(db, now_category_for_parallel_execution):
    patterns = db['patterns'].find({'used': True})

    # Here is a parallel shit
    check_category_id_for_parallel = -100
    categories = db['ontology'].find()
    for category in categories:
        if category['category_name'] == now_category_for_parallel_execution:
            check_category_id_for_parallel = category['_id']
            break
    categories.close()

    for pattern in patterns:

        # Here is a parallel shit
        if pattern['extracted_category_id'] != check_category_id_for_parallel:
            continue

        sp = pattern['string']
        id = pattern['_id']
        p = find_sub_pattern(db, pattern)
        if not p is None:
            counter = 0
            for np in patterns:
                if np['string'] == p['string'] and np['extracted_category_id'] == p['extracted_category_id']:
                    counter += 1
            if counter >= 2:
                #new pattern already exists in db
                db['patterns'].update({'_id': id},
                                      {'$set': {'used':False}})
            else:
                #updating pattern string
                db['patterns'].update({'_id': id},
                                      {'$set': {'string':p['string']}})
            logging.info('Pattern replaced: [' + sp.encode('utf-8') +'] with ['+p['string'].encode('utf-8') + ']')



def main():
    global db
    connect_to_database()
    ppp = open('subpatterns.txt', 'w')
    patterns = db['patterns'].find({'used':True})
    ontology = db['indexes'].find()
    categories = dict()
    for cat in ontology:
        categories[cat['_id']] = cat['category_name']
    for pattern in patterns:
        sp = pattern['string']
        p = find_sub_pattern(db, pattern)
        if not p is None:
            ppp.write(sp.encode('utf-8') + ' __ ' + p['string'].encode('utf-8')+' ___ ' + categories[p['extracted_category_id']].encode('utf-8')+'\n')
    ppp.close()

if __name__ == "__main__":
    main()