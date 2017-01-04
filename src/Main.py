import sys

import time

sys.path.insert(0, '../src/')
import logging
import pickle
import nltk
import os
from tqdm import tqdm
import pymorphy2
import pandas as pd
from pymystem3 import Mystem
from pymongo import MongoClient
import TextProcesser
import PatternExtractor
import InstanceExtractor
import Cleaner

text_dictionary = dict()

morph = pymorphy2.MorphAnalyzer()
mystem = Mystem()

# FIXME enter full path for current files on your computer
ontology_path = '../resources/xlsx/categories_animals_ru.xls'
patterns_pool_path = '../resources/xlsx/patterns.xlsx'
log_path = '../log/cpl.log'

INF = 100 * 100 * 100
ITERATIONS = 100
db = None
cnx = None
MODE = 2

def connect_to_database():
    # client = MongoClient('localhost', 27017)

    client = MongoClient('localhost', 27017)
    global db
    db = client.test

def inizialize():
    # Read initial ontology and patterns
    logging.basicConfig(filename=log_path, filemode='w', level=logging.DEBUG, format='%(asctime)s %(message)s')
    get_patterns_from_file(patterns_pool_path, db)
    logging.info("patterns pool inizializated")
    get_ontology_from_file(ontology_path, db)
    logging.info("ontology inizializated")

def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj

def get_patterns_from_file(file, db):
    logging.info('Extracting initial patterns from file')
    file = pd.read_excel(file)
    for index, row in file.iterrows():
        if db['patterns'].find({'_id': int(row['id'])}).count() != 0:
            continue
        pattern = dict()
        pattern['_id'] = int(row['id'])
        pattern['string'] = row['pattern']

        arg1, arg2 = dict(), dict()
        arg1['case'] = row['arg1_case'].lower()
        arg1['num'] = row['arg1_num'].lower()
        arg1['pos'] = row['arg1_pos'].lower()
        arg2['case'] = row['arg2_case'].lower()
        arg2['num'] = row['arg2_num'].lower()
        arg2['pos'] = row['arg2_pos'].lower()

        pattern['arg1'] = arg1
        pattern['arg2'] = arg2

        pattern['presicion'] = INF
        pattern['true_detective'] = 0
        pattern['false_detective'] = 0
        # -1 in extracted category id in case when it's our initial pattern
        pattern['extracted_category_id'] = -1
        pattern['used'] = True
        pattern['coocurence_count'] = INF

        # FIXME think about this features more deeply later
        pattern['iteration_added'] = list()
        pattern['iteration_deleted'] = list()

        db['patterns'].insert(pattern)


def get_ontology_from_file(file, db):
    print('Extracting initial ontology from file')
    file = pd.read_excel(file)
    for index, row in file.iterrows():
        ontology_category = dict()
        category_name = mystem.lemmatize(row['categoryName'])[0]

        if db['ontology'].find({'category_name': category_name}).count() != 0:
            continue
        ontology_category['category_name'] = category_name
        ontology_category['_id'] = db['ontology'].find().count() + 1
        if type(row['seedInstances']) is float:
            ontology_category['instances'] = list()
        else:
            ontology_category['instances'] = row['seedInstances'].split('"')[1::2]

        if type(row['seedExtractionPatterns']) is float:
            ontology_category['extraction_patterns'] = list()
        else:
            ontology_category['extraction_patterns'] = [int(s) for s in row['seedExtractionPatterns'].split(' ') if
                                                        s.isdigit()]

        ontology_category['promoted_patterns'] = list()
        ontology_category['max_instance_precision'] = 0.0
        ontology_category['max_pattern_precision'] = 0.0

        for instance in ontology_category['instances']:
            promoted_instance = dict()
            promoted_instance['lexem'] = instance
            promoted_instance['_id'] = db['promoted_instances'].find().count() + 1
            promoted_instance['category_name'] = category_name
            promoted_instance['used'] = True
            promoted_instance['precision'] = 1.0
            promoted_instance['extracted_pattern_id'] = -1
            promoted_instance['iteration_added'] = [0]
            promoted_instance['iteration_deleted'] = list()
            # this instances would have the highest precision because was added by default
            promoted_instance['count_in_text'] = INF
            db['promoted_instances'].insert(promoted_instance)

        db['ontology'].insert(ontology_category)


def calc_ngrams_pat(db):
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
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return tmpDict


def calc_ngrams_instances(db):
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
    sentences.close()
    print('Elapsed time: {:.3f} sec'.format(time.time() - startTime))
    return tmpDict


def main():

    #FIXME count of elements in okl files
    max_in_file = 5000000

    #FIXME last indexes of pkl files
    insIndex = 0
    patIndex = 0

    ins_ngrams = dict()
    pat_ngrams = dict()

    ins_length = 0
    pat_length = 0

    MODE = 3

    connect_to_database()
    inizialize()

    #getting text from files and building indexes
    TextProcesser.build_indexes_sceleton(db)
    TextProcesser.preprocess_files(db)


    # slow method. saves ngrams to databse. too slow. I dont know how to make it faster.
    if MODE == 2:
        TextProcesser.ngarms_for_instances(db)
        TextProcesser.ngrams_for_patterns(db)

    # really fast method. saves ngrams in ram. use it in case of not too large texts.
    if MODE == 1:
        pat_ngrams = calc_ngrams_pat(db)
        print('pat_ngrams_length=' + str(len(pat_ngrams)))
        ins_ngrams = calc_ngrams_instances(db)
        print('ins_ngrams_length=' + str(len(ins_ngrams)))

    # method using pkl files.
    if MODE == 3:
        pat_length = TextProcesser.ngrams_patterns_pkl(db, max_in_file, patIndex)
        ins_length = TextProcesser.ngrams_instances_pkl(db, max_in_file, insIndex)


    treshold = 50
    for iteration in range(1, 11):
        startTime = time.time()
        print('Iteration [%s] begins' % str(iteration))
        logging.info('=============ITERATION [%s] BEGINS=============' % str(iteration))
        InstanceExtractor.extract_instances(db, iteration)
        InstanceExtractor.evaluate_instances(db, treshold, iteration,ins_ngrams, MODE, ins_length)
        PatternExtractor.extract_patterns(db, iteration)
        PatternExtractor.evaluate_patterns(db, treshold, iteration, pat_ngrams, MODE, pat_length)
        Cleaner.zero_coocurence_count(db)
        print('Iteration time: {:.3f} sec'.format(time.time() - startTime))

if __name__ == "__main__":
    main()

