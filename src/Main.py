from __future__ import division
import sys
import time
sys.path.insert(0, '../src/')
import logging
import pickle
import pandas as pd
from pymystem3 import Mystem
from pymongo import MongoClient
import TextProcesser
import PatternExtractor
import InstanceExtractor
import Cleaner
import configparser

text_dictionary = dict()

mystem = Mystem()

# FIXME enter full path for current files on your computer
ontology_path = '../resources/xlsx/ontology.xls'
patterns_pool_path = '../resources/xlsx/patterns.xlsx'
log_path = '../log/cpl.log'

INF = 100 * 100 * 100
db = None

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


def main():
    config = configparser.ConfigParser()
    config.read("../config.ini")
    config.sections()
    config_reader = config['DEFAULT']

    # Count of elements in pkl files
    max_in_file = int(config_reader['count'])

    instances_ngrams_last_dict_index = int(config_reader['insDicLast'])
    patterns_ngrams_last_dict_index = int(config_reader['patDicLast'])

    # Flag for using morph info
    use_morph = False
    if (int(config_reader['morph']) == 1):
        use_morph = True

    # Initialising dictionaries for storing ngrams in RAM
    ins_ngrams = dict()
    pat_ngrams = dict()
    ins_length = 0
    pat_length = 0

    # ngrams_mode for ngrams calculation
    ngrams_mode = int(config_reader['ngrams'])

    username = config_reader['u']
    password = config_reader['p']
    now_category = config_reader['c']

    connect_to_database(username, password, "localhost", 27017, now_category)

    # Extracting initial ontology
    if  (int(config_reader['dontinit']) != 1):
        inizialize()

    if now_category == "all":
        now_category = ""

    # getting text from files and building indexes
    if not (int(config_reader['dontindex']) == 1):
        TextProcesser.build_indexes_sceleton(db)
        TextProcesser.preprocess_files(db, now_category)
        
    # really fast method. saves ngrams in ram. use it in case of not too large texts.
    if ngrams_mode == 1:
        pat_ngrams = TextProcesser.calc_ngrams_pat(db)
        print('pat_ngrams_length=' + str(len(pat_ngrams)))
        ins_ngrams = TextProcesser.calc_ngrams_instances(db)
        print('ins_ngrams_length=' + str(len(ins_ngrams)))

    # method using pkl files.
    if ngrams_mode == 2:
        pat_length = TextProcesser.ngrams_patterns_pkl(db, max_in_file, patterns_ngrams_last_dict_index, now_category)
        ins_length = TextProcesser.ngrams_instances_pkl(db, max_in_file, instances_ngrams_last_dict_index, now_category)

    iters = int(config_reader['i']) + 1

    threshold_mode = int(config_reader['tMode'])
    threshold_k_factor = float(config_reader['tK'])
    fixed_threshols_between_zero_and_one = float(config_reader['tT'])
    threshold_fixed_n = int(config_reader['tN'])

    for iteration in range(1, iters):
        startTime = time.time()
        print('Iteration [%s] begins' % str(iteration))
        logging.info('=============ITERATION [%s] BEGINS=============' % str(iteration))
        InstanceExtractor.extract_instances(db, iteration, use_morph)
        InstanceExtractor.evaluate_instances(db, fixed_threshols_between_zero_and_one, threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, ins_ngrams, ngrams_mode, ins_length, now_category)
        PatternExtractor.extract_patterns(db, iteration)
        PatternExtractor.evaluate_patterns(db, fixed_threshols_between_zero_and_one, threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, pat_ngrams, ngrams_mode, pat_length, now_category)
        Cleaner.zero_coocurence_count(db)
        print('Iteration time: {:.3f} sec'.format(time.time() - startTime))


if __name__ == "__main__":
    main()
