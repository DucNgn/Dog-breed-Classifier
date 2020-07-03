import os
import io
import sys
from google.cloud import vision
from google.cloud.vision import types
from flask import Flask, flash, redirect, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    client = vision.ImageAnnotatorClient()

    file_name = os.path.abspath('temp/Miniature-Schnauzer.jpg')
    file_name = os.path.abspath('temp/corgi.jpg')

    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    # Perform label detection
    response = client.label_detection(image=image)
    labels=response.label_annotations

    print(labels, file=sys.stderr)
    
    #for label in labels:
     #   print(label.description, file=sys.stderr)

    return render_template("index.html")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port = port)




