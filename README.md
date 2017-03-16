# NELL (CPL)

Implementation of one of the components of Never Ending Language Learner (Coupled Pattern Learner) for morphologically rich free-word-order language.

## Getting started

To run CPL you need two files: ontology.xlsx - initial ontology for KB and patterns.xlsx - seed patterns for KB.

### Initial ontology

File "ontology.xlsx" contains next rows:
 * categoryName - name for category (lowercase)
 * seedInstances - seed instances for category. Format: "seed1" "seed2" ... "seedN" (all seeds lowercase)
 * seedExtractionPatterns - ids of seed patterns (from patterns.xlsx) to use for category

### Seed patterns

File "patterns.xlsx" contains next rows:
 * id - unique pattern id
 * pattern - pattern text in format [.. (arg1/arg2) .. (arg1/arg2) ..] where arg1==categoryName, arg2==Instance. Example: "arg1, такие как arg2".
 * arg1_case - case of arg1. Format: [nomn/gent/datv/accs/ablt/loct]
 * arg1_case - case of arg2. Format: [nomn/gent/datv/accs/ablt/loct]
 * arg1_num - number of arg1. Format: [plur/sing/all]
 * arg2_num - number of arg2. Format: [plur/sing/all]
 * arg1_pos - part of speech of arg1. Format: [noun/adjf/adjs/comp/verb/infn/prtf/prts/grnd/numr/advb/npro/pred/prep/conj/prcl/intj]
 * arg2_pos - part of speech of arg2. Format: [noun/adjf/adjs/comp/verb/infn/prtf/prts/grnd/numr/advb/npro/pred/prep/conj/prcl/intj]

Read more on http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html

## Structure

 * Put "patterns.xlsx" and "ontology.xlsx" in /resources/xlsx
 * Put texts for text corpus in /resources/categories/category_name/
 * Use config.ini to set configurations
