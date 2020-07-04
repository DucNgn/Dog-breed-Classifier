import os
import io
import sys
import json
import http.client
from google.cloud import vision
from google.cloud.vision import types
from flask import Flask, flash, redirect, request, render_template
from werkzeug.utils import secure_filename

# TEMP environment variables
os.environ['BLACKLIST'] = "./blacklist.json"
os.environ['IMAGE_UPLOAD'] = "./temp"
os.environ['PORT'] = "5000"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './GCloud_credentials.json'

app = Flask(__name__)
app.config["IMAGE_UPLOAD"] = os.environ["IMAGE_UPLOAD"]
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["JPEG", "JPG", "PNG", "GIF"]
app.config["MAX_IMAGE_SIZE"] = 50 * 1024 * 1024

class DogInfo:
    def __init__(self, id, name, breed_group, weight, height, life_span, temperament):
        self.id = id
        self.name = name
        self.breed_group = breed_group
        self.weight = weight
        self.height = height
        self.life_span = life_span
        self.temperament = temperament
    
    def __eq__(self, other):
        if not isinstance(other, DogInfo):
            return NotImplemented
        return self.id == other.id

    def __str__(self):
        output = '''\

            ...ID: {id} 
            ...NAME: {name}
            ...BREED_GROUP: {breed_group}
            ...WEIGHT: {weight}
            ...HEIGHT: {height}
            ...LIFE_SPAN: {life_span}
            ...TEMPERAMENT: {temperament}

            '''.format(id=self.id, name=self.name, breed_group=self.breed_group, weight=self.weight, height=self.height, life_span=self.life_span, temperament=self.temperament)
        return output

@app.route("/")
def index():
    return render_template("index.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template("index.html")

@app.route("/index", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        if request.files:
            if "filesize" in request.cookies:
                if not imageSize_is_allowed(request.cookies["filesize"]):
                    print("Filesize exceed maximum limit")
                    return redirect(request.url)
                
                image = request.files["image"]

                if image.filename == "":
                    return redirect(request.url)

                if image_is_allowed(image.filename):
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config["IMAGE_UPLOAD"], filename))
                    print("Image saved")
                    return redirect(request.url)
                else:
                    print("File extension is not allowed")
                    return redirect(request.url)
    return render_template("index.html")


def image_is_allowed(image_name):
    if not "." in image_name:
        return False
    ext = image_name.rsplit(".", 1)[1]
    return (ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"])

def imageSize_is_allowed(image_size):
    return (int(image_size) <= app.config['MAX_IMAGE_SIZE'])

@app.route("/getResult")
def getResult():
    img_link = "./temp/dog-group-3.jpg"
    (breed, score) = identify_breed(img_link)
    info = getInfo(breed)
    data = addFilters(info)
    for each in data:
        print(each, file=sys.stderr)
    return render_template("index.html")

def addFilters(info):
    data = list()
    for each in info:
        data.append(DogInfo(each['id'], each['name'], each['breed_group'], each['weight'], each['height'], each['life_span'], each['temperament']))
    return data


def identify_breed(img_link):
    client = vision.ImageAnnotatorClient()
    file_name = os.path.abspath(img_link)

    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    # Perform label detection
    response = client.label_detection(image=image)
    labels=response.label_annotations

    blacklist = loadBlacklist()

    best_score = -1
    best_label = str()
    for label in labels:
        if label.description.lower() not in blacklist and label.score >= best_score:
            best_label = label.description
            best_score = label.score
    
    print("\nLABEL: ", best_label, file=sys.stderr)
    print("BEST SCORE: ", best_score, file=sys.stderr)

    return best_label, best_score  

def loadBlacklist():
    blacklistFile = str(os.environ['BLACKLIST'])
    with open(blacklistFile) as blacklist_file:
        data = json.load(blacklist_file)
    blacklist = data['keywords'] + data['breeds']
    for i in range(len(blacklist)):
        blacklist[i] = blacklist[i].lower()
    return blacklist

def getInfo(query):
    conn = http.client.HTTPSConnection("api.thedogapi.com")
    APIKEYFILE = str(os.environ['DOG_API_KEY'])
    with open(APIKEYFILE) as headerFile:
        header = json.load(headerFile)
    querySource = "/v1/breeds/search?q=" + query.replace(" ", "_")

    conn.request("GET", querySource, headers=header)
    res = conn.getresponse()
    data = json.loads(res.read())
    return data
        
if __name__ == '__main__':
    port = int(os.environ['PORT'])
    app.run(debug=True, host='0.0.0.0', port = port)
