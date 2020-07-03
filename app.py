import os
import io
import sys
import json
from google.cloud import vision
from google.cloud.vision import types
from flask import Flask, flash, redirect, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("index.html")

def loadBlacklist():
    blacklistFile = str(os.environ['BLACKLIST'])
    with open(blacklistFile) as blacklist_file:
        data = json.load(blacklist_file)
    blacklist = data['keywords'] + data['breeds']
    return blacklist

@app.route("/getResult")
def getResult():
    results = identify_breed()
    print(results, file=sys.stderr)
    return render_template("index.html")

def identify_breed():
    client = vision.ImageAnnotatorClient()
    file_name = os.path.abspath('temp/golden_retriever.jpg')

    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    # Perform label detection
    response = client.label_detection(image=image)
    labels=response.label_annotations

    results = []
    blacklist = loadBlacklist()
    for label in labels:
        if label.description not in blacklist:
            results.append((label.description, label.score))

    return results    

if __name__ == '__main__':
    port = int(os.environ['PORT'])
    app.run(debug=True, host='0.0.0.0', port = port)




