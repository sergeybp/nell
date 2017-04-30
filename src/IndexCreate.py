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





def create_indexes(db):
    db['patterns'].create_index("used")
    db['promoted_instances'].create_index("category_name")
    db['promoted_instances'].create_index("lexem")
    db['promoted_instances'].create_index("used")
    db['patterns'].create_index("extracted_category_id")
    db['patterns'].create_index("string")
    db['patterns'].create_index("arg1")
    db['patterns'].create_index("arg2")


