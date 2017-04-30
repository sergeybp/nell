from __future__ import division
import sys
import argparse
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
import SubPatterns


text_dictionary = dict()

mystem = Mystem()

# FIXME enter full path for current files on your computer
ontology_path = '../resources/xlsx/ontology.xlsx'
patterns_pool_path = '../resources/xlsx/patterns.xlsx'
log_path = '../log/cpl.log'

INF = 100 * 100 * 100
db = None

def load_dictionary(file):
    with open(file, 'rb') as f:
        obj = pickle.load(f)
    return obj



def connect_to_database(username, password, host, port, catName):
    # client = MongoClient('localhost', 27017)

    if username != "" and password != "":
        uri = 'mongodb://' + username + ':' + password + '@' + host + ':' + str(port) + '/'
        client = MongoClient(uri)
    else:
        client = MongoClient(host, port)
    global db
    db = client[catName]


def main():


    parser = argparse.ArgumentParser()
    parser.add_argument("parallel_category_low_case")
    args = parser.parse_args()
    now_category_for_parallel_execution = args.parallel_category_low_case
    now_category_for_parallel_execution = now_category_for_parallel_execution.decode('utf-8')
    print(now_category_for_parallel_execution)

    logging.basicConfig(filename=log_path+now_category_for_parallel_execution+'.log', filemode='w', level=logging.DEBUG, format='%(asctime)s %(message)s')

    use_morph = True

    # Initialising dictionaries for storing ngrams in RAM
    ins_ngrams = dict()
    pat_ngrams = dict()
    ins_length = 0
    pat_length = 0

    username = ''
    password = ''
    now_category = 'all'
    connect_to_database(username, password, "localhost", 27017, now_category)

    # ngrams_mode for ngrams calculation
    ngrams_mode = 1

    pat_ngrams = TextProcesser.calc_ngrams_pat(db)
    print('pat_ngrams_length=' + str(len(pat_ngrams)))
    ins_ngrams = TextProcesser.calc_ngrams_instances(db)
    print('ins_ngrams_length=' + str(len(ins_ngrams)))



    now_category = ''

    pat_length = 1
    ins_length = 1

    iters = 10

    threshold_mode = 1
    threshold_k_factor = 1
    fixed_threshols_between_zero_and_one = 0.5
    threshold_fixed_n = 500


    for iteration in range(1, iters):
        startTime = time.time()
        print('Category: '+now_category_for_parallel_execution+'    Iteration [%s] begins' % str(iteration))
        logging.info('Category: '+now_category_for_parallel_execution+'   =============ITERATION [%s] BEGINS=============' % str(iteration))
        InstanceExtractor.extract_instances(db, iteration, use_morph, now_category_for_parallel_execution)
        InstanceExtractor.evaluate_instances(db, fixed_threshols_between_zero_and_one, threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, ins_ngrams, ngrams_mode, ins_length, now_category, now_category_for_parallel_execution)
        PatternExtractor.extract_patterns(db, iteration, now_category_for_parallel_execution)
        PatternExtractor.evaluate_patterns(db, fixed_threshols_between_zero_and_one, threshold_mode, threshold_k_factor, threshold_fixed_n, iteration, pat_ngrams, ngrams_mode, pat_length, now_category, now_category_for_parallel_execution)
        Cleaner.zero_coocurence_count(db, now_category_for_parallel_execution)
        SubPatterns.filter_all_patterns(db, now_category_for_parallel_execution)
        print('Category: '+now_category_for_parallel_execution+'  Iteration time: {:.3f} sec'.format(time.time() - startTime))


if __name__ == "__main__":
    main()
