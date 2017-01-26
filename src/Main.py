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
import argparse

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


def connect_to_database(username, password, host, port, catName):
    # client = MongoClient('localhost', 27017)

    if username != "" and password != "":
        uri = 'mongodb://' + username + ':' + password + '@' + host + ':' + str(port) + '/'
        client = MongoClient(uri)
    else:
        client = MongoClient(host, port)
    global db
    db = client[catName]


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
    parser = argparse.ArgumentParser(description='Run CPL algorithm.')
    parser.add_argument("-c", type=str, help='Category name. Default - all categories')
    parser.add_argument("-u", type=str, help='Username for MongoDB')
    parser.add_argument("-p", type=str, help='Password for MongoDB')
    parser.add_argument("-host", type=str, help='Host for MongoDB. Default - localhost.')
    parser.add_argument("-port", type=int, help='Port for MongoDB. Default - 27017')
    parser.add_argument("-i", type=int, help='Iteration count. Default - 10')
    parser.add_argument("-morph", action="store_true", help='Use morph')
    parser.add_argument("-ngrams", type=str,
                        help='Ngrams mode = [1|2|3] 1 - saves ngrams to DB (slow) 2 - saves ngrams to RAM (fast) 3 - saves ngrams to pkl files (recomended)')
    parser.add_argument("-count", type=int, help='Ngrams max count in pkl file. Default - 5000000')
    parser.add_argument("-dontinit", action="store_true", help="Don't extract initial ontology")
    parser.add_argument("-dontindex", action="store_true", help="Don't build indexes")
    parser.add_argument("-insDicLast", type=int, help='Index of last file for instances dicts. Default - 0')
    parser.add_argument("-patDicLast", type=int, help='Index of last file for patternd dicts. Default - 0')

    args = parser.parse_args()

    # Count of elements in pkl files
    if args.count:
        max_in_file = args.count
    else:
        max_in_file = 5000000

    insIndex = 0
    if args.insDicLast:
        insIndex = args.insDicLast

    patIndex = 0
    if args.patDicLast:
        patIndex = args.patDicLast

    # Flag for using morph info
    if args.morph:
        useMorph = True
    else:
        useMorph = False

    # Initialising dictionaries for storing ngrams in RAM
    ins_ngrams = dict()
    pat_ngrams = dict()
    ins_length = 0
    pat_length = 0

    # Mode for ngrams calculation
    if args.ngrams:
        MODE = args.ngrams
    else:
        MODE = 3

    username = ""
    password = ""
    if args.u:
        username = args.u
    if args.p:
        password = args.p

    cat = "all"
    if args.c:
        cat = args.c

    connect_to_database(username, password, "localhost", 27017, cat)

    # Extracting initial ontology
    if not args.dontinit:
        inizialize()

    if cat == "all":
        cat = ""

    # getting text from files and building indexes
    if not args.dontindex:
        TextProcesser.build_indexes_sceleton(db)
        TextProcesser.preprocess_files(db, cat)

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
        pat_length = TextProcesser.ngrams_patterns_pkl(db, max_in_file, patIndex, cat)
        ins_length = TextProcesser.ngrams_instances_pkl(db, max_in_file, insIndex, cat)

    iters = 11
    if args.i:
        iters = args.i + 1
    treshold = 50
    for iteration in range(1, iters):
        startTime = time.time()
        print('Iteration [%s] begins' % str(iteration))
        logging.info('=============ITERATION [%s] BEGINS=============' % str(iteration))
        InstanceExtractor.extract_instances(db, iteration, useMorph)
        InstanceExtractor.evaluate_instances(db, treshold, iteration, ins_ngrams, MODE, ins_length, cat)
        PatternExtractor.extract_patterns(db, iteration)
        PatternExtractor.evaluate_patterns(db, treshold, iteration, pat_ngrams, MODE, pat_length, cat)
        Cleaner.zero_coocurence_count(db)
        print('Iteration time: {:.3f} sec'.format(time.time() - startTime))


if __name__ == "__main__":
    main()
