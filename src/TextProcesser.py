import pandas as pd
from pymystem3 import Mystem
import nltk
from tqdm import tqdm
import pymorphy2
import logging
import pymysql
import pymongo
import pickle
import os
import string
import time

mystem = Mystem()
punctuation = string.punctuation
morph = pymorphy2.MorphAnalyzer()

texts_path = '../resources/testT'
files = [f for f in os.listdir(texts_path) if os.path.isfile(os.path.join(texts_path, f))]
gId = 0


def preprocess_files(db):
    global gId
    gId = 0
    files = [f for f in os.listdir(texts_path) if os.path.isfile(os.path.join(texts_path, f))]
    print('\ntry to find unprocessed text')
    for file in tqdm(files):
        if db['processed_files'].find({'name': file}).count() != 0:
            logging.info('File [%s] is already in database, skipping' % file)
            continue
        file_path = texts_path + '/' + file
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
    sentences = nltk.sent_tokenize(text)
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
            if '[[' in word or ']]' in word or '[' in word or ']' in word or '==' in word or '|' in word or '=' in word:
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


def ngarms_for_instances(db):
    startTime = time.time()
    print('calculating ngrams for instances')
    tmpDict = dict()
    tmpLexems = list()
    counter = 0
    sentences = db['sentences'].find(timeout=False)
    for sentence in sentences:
        words = sentence['words']
        for word in words:
            lexem = word['lexem']
            counter += 1
            try:
                tmpDict[lexem] += 1
            except:
                tmpDict[lexem] = 1
                tmpLexems.append(lexem)
        # FIXME how often changes will be written to db
        if counter % 100000 == 0:
            # save
            for lex in tmpLexems:
                if db['ngrams_instances'].find({'lexem': lex}).count() > 0:
                    tC = db['ngrams_instances'].find_one({'lexem': lex})['count']
                    tC += tmpDict[lex]
                    db['ngrams_instances'].update({'lexem': lex}, {'lexem': lex, 'count': tC})
                else:
                    db['ngrams_instances'].insert({'lexem': lex, 'count': tmpDict[lex]})
            tmpDict = dict()
            tmpLexems = list()
    # save
    for lex in tmpLexems:
        if db['ngrams_instances'].find({'lexem': lex}).count() > 0:
            tC = db['ngrams_instances'].find_one({'lexem': lex})['count']
            tC += tmpDict[lex]
            db['ngrams_instances'].update({'lexem': lex}, {'lexem': lex, 'count': tC})
        else:
            db['ngrams_instances'].insert({'lexem': lex, 'count': tmpDict[lex]})
    tmpDict = dict()
    tmpLexems = list()
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return


def ngrams_for_patterns(db):
    startTime = time.time()
    print('calculating ngrams for patterns')
    tmpDict = dict()
    tmpLexems = list()
    counter = 0
    sentences = db['sentences'].find(timeout=False)
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
                    tmpDict[lexem] += 1
                except:
                    tmpDict[lexem] = 1
                    tmpLexems.append(lexem)
                # FIXME how often changes will be written to db
                if counter % 1000000 == 0:
                    # save
                    for lex in tmpLexems:
                        if db['ngrams_patterns'].find({'lexem': lex}).count() > 0:
                            tC = db['ngrams_patterns'].find_one({'lexem': lex})['count']
                            tC += tmpDict[lex]
                            db['ngrams_patterns'].update({'lexem': lex}, {'lexem': lex, 'count': tC})
                        else:
                            db['ngrams_patterns'].insert({'lexem': lex, 'count': tmpDict[lex]})
                    tmpDict = dict()
                    tmpLexems = list()
    # save
    for lex in tmpLexems:
        if db['ngrams_patterns'].find({'lexem': lex}).count() > 0:
            tC = db['ngrams_patterns'].find_one({'lexem': lex})['count']
            tC += tmpDict[lex]
            db['ngrams_patterns'].update({'lexem': lex}, {'lexem': lex, 'count': tC})
        else:
            db['ngrams_patterns'].insert({'lexem': lex, 'count': tmpDict[lex]})
    tmpDict = dict()
    tmpLexems = list()
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return


def ngrams_patterns_pkl(db, ngrams_in_file, lastPart):
    nowPart = lastPart
    startTime = time.time()
    print('calculating ngrams for patterns')
    tmpDict = dict()
    tmpLexems = list()
    counter = 0
    sentences = db['sentences'].find(timeout=False)
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
                    tmpDict[lexem] += 1
                except:
                    tmpDict[lexem] = 1
                    tmpLexems.append(lexem)
                if len(tmpDict) > ngrams_in_file:

                    toSave = dict()
                    alreadySaved = list()

                    for i in range(nowPart):
                        x = load_dictionary('ngrams_dictionary_for_patterns' + str(i) + '.pkl')
                        for lex in tmpLexems:
                            try:
                                r = x[lex]
                                x[lex] = x[lex] + tmpDict[lex]
                                alreadySaved.append(lex)
                            except:
                                r = 1
                        with open('ngrams_dictionary_for_patterns' + str(i) + '.pkl', 'wb') as f:
                            pickle.dump(x, f)
                    for lex in tmpLexems:
                        if not lex in alreadySaved:
                            toSave[lex] = tmpDict[lex]
                    with open('ngrams_dictionary_for_patterns' + str(nowPart) + '.pkl', 'wb') as f:
                        pickle.dump(toSave, f)
                    nowPart += 1
                    tmpDict = dict()
                    tmpLexems = list()
    # save
    toSave = dict()
    alreadySaved = list()

    for i in range(nowPart):
        x = load_dictionary('ngrams_dictionary_for_patterns' + str(i) + '.pkl')
        for lex in tmpLexems:
            try:
                r = x[lex]
                x[lex] = x[lex] + tmpDict[lex]
                alreadySaved.append(lex)
            except:
                r = 1
        with open('ngrams_dictionary_for_patterns' + str(i) + '.pkl', 'wb') as f:
            pickle.dump(x, f)
    for lex in tmpLexems:
        if not lex in alreadySaved:
            toSave[lex] = tmpDict[lex]
    with open('ngrams_dictionary_for_patterns' + str(nowPart) + '.pkl', 'wb') as f:
        pickle.dump(toSave, f)
    nowPart += 1
    tmpDict = dict()
    tmpLexems = list()
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return nowPart


def ngrams_instances_pkl(db, ngrams_in_file, lastPart):
    nowPart = lastPart
    startTime = time.time()
    print('calculating ngrams for instances')
    tmpDict = dict()
    tmpLexems = list()
    counter = 0
    sentences = db['sentences'].find(timeout=False)
    for sentence in sentences:
        words = sentence['words']
        for word in words:
            lexem = word['lexem']
            counter += 1
            try:
                tmpDict[lexem] += 1
            except:
                tmpDict[lexem] = 1
                tmpLexems.append(lexem)
                if len(tmpDict) > ngrams_in_file:

                    toSave = dict()
                    alreadySaved = list()

                    for i in range(nowPart):
                        x = load_dictionary('ngrams_dictionary_for_instances' + str(i) + '.pkl')
                        for lex in tmpLexems:
                            try:
                                r = x[lex]
                                x[lex] = x[lex] + tmpDict[lex]
                                alreadySaved.append(lex)
                            except:
                                r = 1
                        with open('ngrams_dictionary_for_instances' + str(i) + '.pkl', 'wb') as f:
                            pickle.dump(x, f)
                    for lex in tmpLexems:
                        if not lex in alreadySaved:
                            toSave[lex] = tmpDict[lex]
                    with open('ngrams_dictionary_for_instances' + str(nowPart) + '.pkl', 'wb') as f:
                        pickle.dump(toSave, f)
                    nowPart += 1
                    tmpDict = dict()
                    tmpLexems = list()
    # save
    toSave = dict()
    alreadySaved = list()

    for i in range(nowPart):
        x = load_dictionary('ngrams_dictionary_for_instances' + str(i) + '.pkl')
        for lex in tmpLexems:
            try:
                r = x[lex]
                x[lex] = x[lex] + tmpDict[lex]
                alreadySaved.append(lex)
            except:
                r = 1
        with open('ngrams_dictionary_for_instances' + str(i) + '.pkl', 'wb') as f:
            pickle.dump(x, f)
    for lex in tmpLexems:
        if not lex in alreadySaved:
            toSave[lex] = tmpDict[lex]
    with open('ngrams_dictionary_for_instances' + str(nowPart) + '.pkl', 'wb') as f:
        pickle.dump(toSave, f)
    nowPart += 1
    tmpDict = dict()
    tmpLexems = list()
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return nowPart


def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj
