from __future__ import division
import nltk
from tqdm import tqdm
import pymorphy2
import logging
import pickle
import os
import string
import time

punctuation = string.punctuation
morph = pymorphy2.MorphAnalyzer()

texts_path = '../resources/categories'
files = [f for f in os.listdir(texts_path) if os.path.isfile(os.path.join(texts_path, f))]


def preprocess_files(db, now_category_name):
    texts_pathN = texts_path + '/' + now_category_name
    global gId
    gId = 0

    paths = dict()

    files = [f for f in os.listdir(texts_pathN) if os.path.isfile(os.path.join(texts_pathN, f))]
    if now_category_name == "":
        files = [f for f in os.listdir(texts_path) if os.path.isdir(os.path.join(texts_path, f))]
        tmp_list_for_files = list()
        for fa in files:
            kI = [f for f in os.listdir(texts_path+'/'+fa) if os.path.isfile(os.path.join(texts_path+'/'+fa, f))]
            for ff in kI:
                paths[ff] = texts_path+'/'+fa+'/'+ff
            tmp_list_for_files = tmp_list_for_files + kI
        files = tmp_list_for_files
    print('\ntry to find unprocessed text')
    for file in tqdm(files):
        if db['processed_files'].find({'name': file}).count() != 0:
            logging.info('File [%s] is already in database, skipping' % file)
            continue
        file_path = texts_pathN + '/' + file
        if now_category_name == "":
            file_path = paths[file]
        process_sentences_from_file(file_path, db)
        db['processed_files'].insert({'name': file})
        logging.info('File [%s] was sucessfully added to database' % file)


def build_indexes_sceleton(db):
    categories = db['ontology'].find()
    for category in categories:
        index = dict()
        index['sentences_id'] = list()
        index['_id'] = db['indexes'].find().count() + 1
        index['category_name'] = category['category_name']
        db['indexes'].insert(index)
    categories.close()
    print('prebuilded indexes')


def process_sentences_from_file(file, db):
    lId = db['sentences'].find().count() + 1
    catNames = list()
    categories = db['ontology'].find()
    for category in categories:
        catNames.append(category['category_name'])
    categories.close()
    text = open(file, 'r').read()
    sentences = nltk.sent_tokenize(text.decode('utf-8'))
    for s in sentences:
        sentence = dict()
        sentence['_id'] = lId
        sentence['string'] = s
        sentence['words'] = list()
        words = nltk.word_tokenize(s)
        reallyNeeded = False
        tmpCategoryName = list()
        for word in words:
            word_dict = dict()
            if '[[' in word or ']]' in word or '[' in word or ']' in word or '==' in word or '|' in word or '=' in word or '{{' in word or '}}' in word:
                continue
            word_dict['original'] = word
            if word in punctuation:
                word_dict['punctuation'] = True
                word_dict['lexem'] = word
                sentence['words'].append(word_dict)
                continue

            p = morph.parse(word)
            word_dict['pos'] = p[0].tag.POS
            word_dict['case'] = p[0].tag.case
            word_dict['lexem'] = p[0].normal_form

            # checking if really needed
            for name in catNames:
                if name == word_dict['lexem']:
                    reallyNeeded = True
                    tmpCategoryName.append(name)
            word_dict['number'] = p[0].tag.number
            word_dict['punctuation'] = False
            sentence['words'].append(word_dict)

        # adding in database if needed and updating indexes
        if reallyNeeded:
            lId += 1
            for tmpCatName in tmpCategoryName:
                preIndex = db['indexes'].find_one({'category_name': tmpCatName})
                preIndex['sentences_id'].append(sentence['_id'])
                db['indexes'].update({'category_name': tmpCatName}, {'category_name': preIndex['category_name'],
                                                                     'sentences_id': preIndex['sentences_id'],
                                                                     '_id': preIndex['_id']})
            db['sentences'].insert(sentence)
    return

def ngrams_patterns_pkl(db, ngrams_in_file, last_part_dictionary_number, cat):
    now_part = last_part_dictionary_number
    startTime = time.time()
    print('calculating ngrams for patterns')
    tmp_dictionary = dict()
    tmp_list_lexems = list()
    counter = 0
    sentences = db['sentences'].find()
    for sentence in sentences:
        tWords = sentence['words']
        words = list()
        for w in tWords:
            words.append(w['original'])
        for i in range(1, 3 + 1):
            ngrams = nltk.ngrams(words, i)
            for ngram in ngrams:
                s = ''
                for word in ngram:
                    s += word
                    s += ' '
                s = s[:-1].lower()
                lexem = s
                counter += 1
                try:
                    tmp_dictionary[lexem] += 1
                except:
                    tmp_dictionary[lexem] = 1
                    tmp_list_lexems.append(lexem)
                if len(tmp_dictionary) > ngrams_in_file:

                    toSave = dict()
                    alreadySaved = list()

                    for i in range(now_part):
                        x = load_dictionary('ngrams_dictionary_for_patterns.' + cat + '.' + str(i) + '.pkl')
                        for lex in tmp_list_lexems:
                            try:
                                x[lex] = x[lex] + tmp_dictionary[lex]
                                alreadySaved.append(lex)
                            except:
                                pass
                        with open('ngrams_dictionary_for_patterns.' + cat + '.' + str(i) + '.pkl', 'wb') as f:
                            pickle.dump(x, f)
                    for lex in tmp_list_lexems:
                        if not lex in alreadySaved:
                            toSave[lex] = tmp_dictionary[lex]
                    with open('ngrams_dictionary_for_patterns.' + cat + '.' + str(now_part) + '.pkl', 'wb') as f:
                        pickle.dump(toSave, f)
                    now_part += 1
                    tmp_dictionary = dict()
                    tmp_list_lexems = list()
    # save
    toSave = dict()
    alreadySaved = list()

    for i in range(now_part):
        x = load_dictionary('ngrams_dictionary_for_patterns.' + cat + '.' + str(i) + '.pkl')
        for lex in tmp_list_lexems:
            try:
                x[lex] = x[lex] + tmp_dictionary[lex]
                alreadySaved.append(lex)
            except:
                pass
        with open('ngrams_dictionary_for_patterns.' + cat + '.' + str(i) + '.pkl', 'wb') as f:
            pickle.dump(x, f)
    for lex in tmp_list_lexems:
        if not lex in alreadySaved:
            toSave[lex] = tmp_dictionary[lex]
    with open('ngrams_dictionary_for_patterns.' + cat + '.' + str(now_part) + '.pkl', 'wb') as f:
        pickle.dump(toSave, f)
    now_part += 1
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return now_part


def ngrams_instances_pkl(db, ngrams_in_file, last_part_dictionary_number, cat):
    now_part = last_part_dictionary_number
    startTime = time.time()
    print('calculating ngrams for instances')
    tmp_dictionary = dict()
    tmp_list_lexems = list()
    counter = 0
    sentences = db['sentences'].find()
    for sentence in sentences:
        words = sentence['words']
        for word in words:
            lexem = word['lexem']
            counter += 1
            try:
                tmp_dictionary[lexem] += 1
            except:
                tmp_dictionary[lexem] = 1
                tmp_list_lexems.append(lexem)
                if len(tmp_dictionary) > ngrams_in_file:
                    toSave = dict()
                    alreadySaved = list()
                    for i in range(now_part):
                        x = load_dictionary('ngrams_dictionary_for_instances.' + cat + '.' + str(i) + '.pkl')
                        for lex in tmp_list_lexems:
                            try:
                                x[lex] = x[lex] + tmp_dictionary[lex]
                                alreadySaved.append(lex)
                            except:
                                pass
                        with open('ngrams_dictionary_for_instances.' + cat + '.' + str(i) + '.pkl', 'wb') as f:
                            pickle.dump(x, f)
                    for lex in tmp_list_lexems:
                        if not lex in alreadySaved:
                            toSave[lex] = tmp_dictionary[lex]
                    with open('ngrams_dictionary_for_instances.' + cat + '.' + str(now_part) + '.pkl', 'wb') as f:
                        pickle.dump(toSave, f)
                    now_part += 1
                    tmp_dictionary = dict()
                    tmp_list_lexems = list()
    # save
    toSave = dict()
    alreadySaved = list()

    for i in range(now_part):
        x = load_dictionary('ngrams_dictionary_for_instances.' + cat + '.' + str(i) + '.pkl')
        for lex in tmp_list_lexems:
            try:
                x[lex] = x[lex] + tmp_dictionary[lex]
                alreadySaved.append(lex)
            except:
                pass
        with open('ngrams_dictionary_for_instances.' + cat + '.' + str(i) + '.pkl', 'wb') as f:
            pickle.dump(x, f)
    for lex in tmp_list_lexems:
        if not lex in alreadySaved:
            toSave[lex] = tmp_dictionary[lex]
    with open('ngrams_dictionary_for_instances.' + cat + '.' + str(now_part) + '.pkl', 'wb') as f:
        pickle.dump(toSave, f)
    now_part += 1
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return now_part


def calc_ngrams_pat(db):
    startTime = time.time()
    print('calculating ngrams for patterns')
    tmp_dictionary = dict()
    tmp_list_lexems = list()
    counter = 0
    sentences = db['sentences'].find()
    for sentence in sentences:
        tWords = sentence['words']
        words = list()
        for w in tWords:
            words.append(w['original'])
        for i in range(1, 3 + 1):
            ngrams = nltk.ngrams(words, i)
            for ngram in ngrams:
                s = ''
                for word in ngram:
                    s += word
                    s += ' '
                s = s[:-1].lower()
                lexem = s
                counter += 1
                try:
                    tmp_dictionary[lexem] += 1
                except:
                    tmp_dictionary[lexem] = 1
                    tmp_list_lexems.append(lexem)
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return tmp_dictionary


def calc_ngrams_instances(db):
    startTime = time.time()
    print('calculating ngrams for instances')
    tmp_dictionary = dict()
    tmp_list_lexems = list()
    counter = 0
    sentences = db['sentences'].find()
    for sentence in sentences:
        words = sentence['words']
        for word in words:
            lexem = word['lexem']
            counter += 1
            try:
                tmp_dictionary[lexem] += 1
            except:
                tmp_dictionary[lexem] = 1
                tmp_list_lexems.append(lexem)
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return tmp_dictionary


def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj
