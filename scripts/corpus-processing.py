import argparse
from pymystem3 import Mystem
import re
import logging, os, sys
import time
import json
from os import listdir
from os.path import isfile, join
from multiprocessing import Pool

mystem = None
logger = None
dictionary = dict()

def find_lexema(word, strLex):
    try:
        grStr = word[0]['analysis'][0]['gr']
        if(strLex in grStr):
            return True
        else:
            return False
    except Exception:
        return False


def get_prev_word(text_corpus, position):
    word = ''
    if(text_corpus[position] == '.'):
        return ''
    if(text_corpus[position] == ' '):
       position -= 1
    for letter in reversed(range(position + 1)):
        if(text_corpus[letter] == ' ' or text_corpus[letter] == '.'):
            break
        word = word + text_corpus[letter]
    word = word[::-1]
    return word


def get_next_word(text_corpus, position):
    word = ''
    if(text_corpus[position] == '.'):
        return ''
    if(text_corpus[position] == ' '):
        position += 1
    for letter in range(position, len(text_corpus)):
        if(text_corpus[letter] == ' ' or text_corpus[letter] == '.'):
            break
        word = word + text_corpus[letter]
    return word


def find_part_of_speech_before(text_corpus, position, parts_of_speech, strict = True):
    word = ''
    counter = 0
    while counter <= 100:
        counter += 1
        flag = False
        word = get_prev_word(text_corpus, position)
        if(len(word) == 1 or len(word) == 0):
            return ''
        position = position - len(word) - 1
        word_stem = mystem.analyze(word)
        for part_of_speech in parts_of_speech:
            if not find_lexema(word_stem, part_of_speech):
                flag = True
        if not flag:
            if strict and (find_lexema(word_stem, '|')):
                return ''
            return word

    return word


def find_first_part_of_speech_next(text_corpus, position, parts_of_speech, strict = True):
    word = ''
    counter = 0
    while counter <= 5:
        counter += 1
        word = get_next_word(text_corpus, position)
        if(len(word) == 1 or len(word) == 0):
            return ''
        position += len(word) + 1
        word_stem = mystem.analyze(word)
        flag = False
        for part_of_speech in parts_of_speech:
            if not find_lexema(word_stem, part_of_speech):
                flag = True
        if not flag:
            if strict and (find_lexema(word_stem, '|')):
                return ''
            return word

    return ''


def set_mystem():
    global mystem
    mystem = Mystem()


def check_dictionary(gain):
    if (dictionary.__len__() > 1000000):
        gain += 1
    global dictionary
    keys = list(dictionary.keys())
    for key in keys:
        if(dictionary[key] <= gain):
            dictionary.pop(key)


def define_words(text_corpus, result, parts_of_speech_1, parts_of_speech_2, logger, strict = False):

    word_1 = find_part_of_speech_before(text_corpus, result.start(), parts_of_speech_1)
    word_2 = find_first_part_of_speech_next(text_corpus, result.end(), parts_of_speech_2)
    if word_1 == '' or word_2 == '':
        return

    word_1_stem = mystem.analyze(word_1)
    word_2_stem = mystem.analyze(word_2)
    try:
        word_1 = word_1_stem[0]['analysis'][0]['lex']
    except Exception:
        word_1 = word_1
    try:
        word_2 = word_2_stem[0]['analysis'][0]['lex']
    except Exception:
        word_2 = word_2


    logger.info('Found SUBCATEGORY: [%s], RELATION: [%s], CATEGORY: [%s]', word_1, result.group(), word_2)
    logger.info('CONTEXT: [%s] \n', text_corpus[result.start() - 80:result.start() + 80])

    global dictionary
    dict_key = word_1 + ' ' + word_2
    try:
        dictionary[dict_key] += 1
    except:
        dictionary.update({dict_key:1})

    return


def find_patterns(text_corpus):


    pattern = re.compile(u'\s((относ[ия]тся)\s(к)\s)', re.UNICODE)
    for result in re.finditer(pattern, text_corpus):
        # for pattern "относятся к"
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'род'], logger, strict=True)
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'дат'], logger, strict=True)


    pattern = re.compile(u'\s(явля[ею]тся\s)', re.UNICODE)
    for result in re.finditer(pattern, text_corpus):
        # for pattern "являются"
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'твор'], logger, strict=True)


    pattern = re.compile(u'\s(счита[ею]тся\s)', re.UNICODE)
    for result in re.finditer(pattern, text_corpus):
        # for pattern "считаются"
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'твор'], logger, strict=True)


    pattern = re.compile(u'\s(-)\s(это\s)', re.UNICODE)
    for result in re.finditer(pattern, text_corpus):
        # for pattern "считаются"
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'им'], logger, strict=True)


    pattern = re.compile(u'\s(-)\s', re.UNICODE)
    for result in re.finditer(pattern, text_corpus):
        # for pattern "считаются"
        define_words(text_corpus, result, ['S,', 'им'], ['S,', 'им'], logger, strict=True)

    return 0


def setup_logger(logger_name, log_file, level=logging.INFO):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)


def main():
    parser = argparse.ArgumentParser(description =' Text corpus file')
    parser.add_argument("-path", type = str, help = 'Path to json with pagenames')
    parser.add_argument("-mode", type=str, help='[s/f] - single fiяle or folder with texts')

    args = parser.parse_args()

    # logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
    #                 datefmt='%Y-%m-%d %H:%M:%S',
    #                 level=logging.INFO,
    #                 filename='results/parser.log',
    #                 filemode='a')

    global logger
    setup_logger('simple', 'results/corpus.log')
    logger = logging.getLogger('simple')


    set_mystem()
    pool = Pool(processes=4)

    if(args.mode == 's'):
        corpus = open(args.path, errors='ignore')
        text_corpus = corpus.read()
        find_patterns(text_corpus)
    result = None
    if(args.mode == 'f'):
        files = [f for f in listdir(args.path) if isfile(join(args.path, f))]
        for file in files:
            filename = args.path + file
            corpus = open(filename, errors='ignore')
            text_corpus = corpus.read()
            find_patterns(text_corpus)
            check_dictionary(1)

    with open('results/dictionary.json', 'w') as jsonfile:
        json.dump(dictionary, jsonfile, ensure_ascii=False)

    return


if __name__ == "__main__":
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))