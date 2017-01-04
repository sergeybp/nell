import argparse
import json
import wikipedia
import codecs

def main():
    parser = argparse.ArgumentParser(description='Downloading wikipedia category page')
    parser.add_argument("-file", type = str, help='Path to json with pagenames')
    parser.add_argument("-num", type = int, help='Number of pages to extract, use "-1" for all pages from file')

    wikipedia.set_lang("ru")

    args = parser.parse_args()
    file = open(args.file, 'r')
    categories = json.load(file)
    punctuation = ['.', ',', '=', '==', '===']

    part = 0
    filename = 'resources/pages/text-corpus.part' + str(part) + '.txt'
    corpus = codecs.open(filename, 'w', errors='ignore')

    if args.num == -1:
        pages_num = int(categories[u'*'][0][u'a'][u'*'].__len__())
    else:
        pages_num = int(args.num)

    for i in range(0, pages_num):
        if int(i/100) != part:
            part += 1
            print(str(i) + '/' + str(pages_num))
            filename = 'resources/pages/text-corpus.part' + str(part) + '.txt'
            corpus = codecs.open(filename, 'w', errors='ignore')
        category_name = ''
        page = ''
        try:
            category_name = categories[u'*'][0][u'a'][u'*'][i][u'title']
        except Exception:
            continue
        if category_name != '':
            try:
                page = wikipedia.page(category_name).content
            except Exception:
                continue
            if(page != ''):
                page = ' '.join([word for word in page.split() if word not in punctuation])
                page = page.replace(',', '')
                #page = page.encode('utf8')
                corpus.write(page)
                print(category_name)

    corpus.close()
    return

if __name__ == "__main__":
    main()