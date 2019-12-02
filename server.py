import sys
from flask import Flask, jsonify, request, render_template
import pysolr
import csv  
import json  
import pandas as pd
import os

import spacy

nlp = spacy.load('vi_spacy_model')
solr = pysolr.Solr('http://localhost:8983/solr/dantri', always_commit=True)

static_folder = os.path.dirname(os.path.realpath(__file__))+'/static/'
app = Flask(__name__, static_folder=static_folder)
app.config['JSON_AS_ASCII'] = False


def tokenizer(doc):
    return nlp(doc).text

def basic_search(general_text):
    text = tokenizer(general_text)
    results = solr.search(text)
    results = [clean(result) for result in results]
    return results

def clean(result):
    for key in result.keys() :
        if key == '_version_':
            continue

        if type(result[key]) == list:
            result[key] = ','.join(result[key])
        result[key] = result[key].replace('_', ' ')
    return result

def advance_search(title, description, content, author, category):
    return


@app.route('/basic_search', methods=['GET'])
def get_basic_search_page():
    return render_template('basic_search.html')


@app.route('/advance_search', methods=['GET'])
def get_advance_search_page():
    return render_template('advance_search.html')


@app.route('/result_search', methods=['GET'])
def search():
    general_text = request.args.get('general_text')

    title = request.args.get('title')
    description = request.args.get('description')
    content = request.args.get('content')
    author = request.args.get('author')
    category = request.args.get('category')

    if general_text != None:
        results = basic_search(general_text)
    else:
        results = advance_search(title, description, content, author, category)

    # return jsonify(general_text, title, description, content, category)
    # return jsonify(results)
    return render_template('result_search.html', results = results)


@app.route('/add_csv_file', methods=['POST'])
def add_csv_file():
    file = request.files['file']
    cols = ['description', 'title', 'content', 'author', 'tag', 'link', 'category']
    df = pd.read_csv(file, usecols = cols, encoding='utf8')

    json_rows = []
    for index, row in df.iterrows():
        json_row = {
            "description" : tokenizer(row["description"]),
            "title"       : tokenizer(row["title"]),
            "content"     : tokenizer(row["content"]),
            "author"      : tokenizer(row["author"]).split(','),
            "tag"         : tokenizer(row["tag"]).split(','),
            "link"        : row["link"],
            "category"    : row["category"]
        }
        json_rows.append(json_row)

    # solr.add(json_rows)
    return jsonify(json_rows), 200

@app.route('/delete_all', methods=['POST'])
def delete_all():
    # solr.delete(q='*:*')
    return jsonify('ok'), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port listening')
    args = parser.parse_args()
    port = args.port
    app.debug = True
    app.run(host='0.0.0.0', port=port)
    
