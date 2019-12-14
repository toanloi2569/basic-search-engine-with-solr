import sys
from flask import Flask, jsonify, request, render_template
from werkzeug.utils import secure_filename
import pysolr
import csv  
import json  
import pandas as pd
import os

import spacy

nlp = spacy.load('vi_spacy_model')
# Gán url search cho pysolr
solr = pysolr.Solr('http://localhost:8983/solr/dantri', always_commit=True)
UPLOAD_FOLDER = '/uploads'

static_folder = os.path.dirname(os.path.realpath(__file__))+'/static/'
app = Flask(__name__, static_folder=static_folder)
app.config['JSON_AS_ASCII'] = False
app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.realpath(__file__))+'/uploads/'


def tokenizer(doc):
    if type(doc) is str:
        return nlp(doc).text
    else:
        return ''



# Xử lý câu truy vấn cơ bản
def basic_search(text):
    text = tokenizer(text)
    # search bằng pysolr
    results = solr.search(text, **{
        'rows':100,
        'hl':'true',
        'hl.method':'original',
        'hl.simple.pre':'<mark style="background-color:#ffff0070;">',
        'hl.simple.post':'</mark>',
        'hl.highlightMultiTerm':'true',
        'hl.fragsize':200,
        'defType' : 'dismax',
        'fl' : '*, score',
        'qf':'tag^3.0 title^3.0 description^2.0 content^1.0 author^1.0',
    })
    
    results = get_results(results)
    return results



# Xử lý câu truy vấn nâng cao
def advance_search(title, description, content, author, category):
    title       = "title:"  + tokenizer(title) if title != "" else ""
    description = "description:" +  tokenizer(description) if description != "" else ""
    content     = "content:" + tokenizer(content) if content != ""  else ""
    author      = "author:" +  tokenizer(author) if author != ""  else ""
    category    = "category:" + category.lower().replace(" ","-") if category != ""  else ""

    q = category + " " + title + description + content + author
    results = solr.search(q, **{
        'rows':10,
        'hl':'true',
        'hl.method':'original',
        'hl.simple.pre':'<mark style="background-color:#ffff0070;">',
        'hl.simple.post':'</mark>',
        'hl.highlightMultiTerm':'true',
        'hl.fragsize':70,
        'defType' : 'edismax',
        'fl' : '*, score',
        'qf':'category^4.0 title^3.0 description^2.0 author^2.0 content^1.0',
    })
    
    results = get_results(results)
    return results



# Hàm này trả về kết quả có highlight
def get_results(results):
    highlight = list(results.highlighting.values())
    result_list = list()
    for i,result in enumerate(results):
        for key in result.keys() :
            if key == '_version_' or key == '_default_text_':
                result[key] = ''
                continue

            if type(result[key]) == list:
                result[key] = ','.join(result[key])
            if type(result[key]) == str:
                result[key] = result[key].replace('_', ' ')

        if len(highlight) != 0:
            result["highlight"] = result["description"][:100] + "..."
            for key in highlight[i].keys():
                result["highlight"] += "...".join(highlight[i][key])
            result["highlight"] = result["highlight"].replace('_', ' ') + "..."

        result_list.append(result)
    return result_list



@app.route('/', methods=['GET'])
def get_main_page():
    return render_template('basic_search.html')



@app.route('/basic_search', methods=['GET'])
def get_basic_search_page():
    return render_template('basic_search.html')



@app.route('/advance_search', methods=['GET'])
def get_advance_search_page():
    return render_template('advance_search.html')



# Xử lý điều hướng câu truy vấn từ client gửi đến
@app.route('/result_search', methods=['GET'])
def search():
    general_text = request.args.get('general_text')

    title       = request.args.get('title')
    description = request.args.get('description')
    content     = request.args.get('content')
    author      = request.args.get('author')
    category    = request.args.get('category')

    query       = request.args
    if general_text != None:
        results = basic_search(general_text)
    else:
        results = advance_search(title, description, content, author, category)
    return render_template('result_search.html', results = results, query = query)



@app.route('/more_like/<id>', methods=['GET'])
def more_like(id):
    results = solr.more_like_this(q=f'id:{id}', mltfl='content', mltmintf=3)
    results = get_results(results)
    return render_template('more_like.html', results = results)



@app.route('/add_csv_file', methods=['GET', 'POST'])
def add_csv_file():
    if request.method == 'GET':
        return render_template('add_file.html')
    
    file = request.files['file']
    if file :
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
    else :
        return jsonify('cant read file')

    cols = ['description', 'title', 'content', 'author', 'tag', 'link', 'category']
    df = pd.read_csv(file_path, usecols = cols, encoding='utf8')

    json_rows = []
    for index, row in df.iterrows():
        json_row = {
            "description" : row["description"],
            "title"       : row["title"],
            "content"     : row["content"],
            "author"      : row["author"].split(',') if type(row["author"]) is str else '',
            "tag"         : row["tag"].split(',') if type(row["tag"]) is str else '',
            "link"        : row["link"],
            "category"    : row["category"]
        }
        json_rows.append(json_row)

    solr.add(json_rows)
    return jsonify('updated'), 200



@app.route('/delete_all', methods=['POST'])
def delete_all():
    solr.delete(q='*:*')
    return jsonify('ok'), 200



if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port listening')
    args = parser.parse_args()
    port = args.port
    app.debug = True
    app.run(host='0.0.0.0', port=port)
    
