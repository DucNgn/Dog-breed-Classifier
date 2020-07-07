import os, io, sys, json
from os import listdir
from hashlib import md5
from time import localtime
import http.client
from google.cloud import vision
from google.cloud.vision import types
from flask import Flask, flash, redirect, request, render_template
from werkzeug.utils import secure_filename

# Config environment variables
os.environ['IMAGE_UPLOAD'] = "./temp"
app = Flask(__name__, static_folder="temp")
app.config["IMAGE_UPLOAD"] = os.environ["IMAGE_UPLOAD"]
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["JPEG", "JPG", "PNG"]
app.config["MAX_IMAGE_SIZE"] = 50 * 1024 * 1024

class DogInfo:
    def __init__(self, id = "-1", name = "Unknown", breed_group="Unknown", weight="Unknown", height="Unknown", life_span="Unknown", temperament='Unknown'):
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

    def makeDict(self):
        return {'Breed Name': self.name, 'Breed Group': self.breed_group, 'weight (imperial)': self.weight['imperial'], 'weight (metric)': self.weight['metric'], 'height (imperial)': self.height['imperial'], 'height (metric)': self.height['metric'], 'life span': self.life_span, 'temperament': self.temperament}

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

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route("/index", methods=["GET", "POST"])
def upload_image():
    tempLocation = str(os.environ['IMAGE_UPLOAD'])
    if request.method == "POST":
        if not os.path.exists(tempLocation):
            os.makedirs(tempLocation)

        if request.files:
            if "filesize" in request.cookies:
                image = request.files["image"]

                if not imageSize_is_allowed(request.cookies["filesize"]):
                    # Check for file size limit
                    flash("File size exceeds maximum limit", "warning")
                    return redirect(request.url)

                if image.filename == "":
                    # Check if it is not empty file
                    flash("Please upload an image to begin", "warning")
                    return redirect(request.url)

                if not image_is_allowed(image.filename):
                    # Check extension of the file
                    flash("File extension is not allowed", "warning")
                    return redirect(request.url)
                else:
                    filename = secure_filename(image.filename)
                    imgPath = os.path.join(tempLocation, filename)
                    image.save(imgPath)
                    print("Image saved")
                    (isDog, breed, score, data) = getResult(imgPath)
                    # Check if the image contains a dog
                    if isDog:
                        tempImgPath = generateImgPath(tempLocation, filename)
                        os.rename(imgPath, tempImgPath)
                        data = make_Dicts(data)
                        score = str(score * 100) + " %"
                        if data:
                            return render_template("result.html", provided_img = tempImgPath, label=breed, score=score, data = data, claimer="The detail info is as followed", visibility="visible")
                        else:
                            return render_template("result.html", provided_img = tempImgPath, label=breed, score=score, data = data, claimer="Unfortunately, no data is available", visibility="hidden")
                    else:
                        flash("Cannot detect a dog breed in the provided image", "info")
                        clean_Tempdir(tempLocation, filename)
                        return redirect(request.url)
    return render_template("index.html")

def generateImgPath(tempLocation, filename):
    prefix = "tempImg." + md5(str(localtime()).encode('utf-8')).hexdigest()
    tempImgName = f"{prefix}__{filename}"
    return os.path.join(tempLocation, tempImgName) 

def make_Dicts(data):
    lst =[]
    for each in data:
        lst.append(each.makeDict())
    return lst

def clean_Tempdir(tempLocation, filename):
    dirPath = os.path.join(tempLocation, filename)
    os.remove(dirPath)

def image_is_allowed(image_name):
    if not "." in image_name:
        return False
    ext = image_name.rsplit(".", 1)[1]
    return (ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"])

def imageSize_is_allowed(image_size):
    return (int(image_size) <= app.config['MAX_IMAGE_SIZE'])

def getResult(img_link):
    (isDog, breed, score) = identify_breed(img_link)
    if not isDog:
        return False, None, None, None
    info = getInfo(breed)
    data = addFilters(info)
    for each in data:
        print(each, file=sys.stderr)
    return True, breed, score, data

def addFilters(info):
    data = list()
    # Validate data returned by the API service
    for each in info:
        if 'id' not in each:
            each['id'] = "-1"
        if 'name' not in each:
            each['name'] = "Unavailable"
        if 'breed_group' not in each:
            each['breed_group'] = "No data"
        if 'weight' not in each:
            each['weight'] = "No data"
        if 'height' not in each:
            each['height'] = "No data"
        if 'life_span' not in each:
            each['life_span'] = "No data"
        if 'temperament' not in each:
            each['temperament'] = "No data"
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
    return is_Dog_Label(labels), best_label, best_score  

def is_Dog_Label(labels):
    for label in labels:
        if label.description.lower() == "dog":
            return True
    return False

def loadBlacklist():
    blacklistFile = str(os.environ['BLACKLIST'])
    with open(blacklistFile) as blacklist_file:
        data = json.load(blacklist_file)
    blacklist = data['keywords'] + data['breeds']
    for i in range(len(blacklist)):
        blacklist[i] = blacklist[i].lower()
    return blacklist

def getInfo(query):
    # Get information about a breed via an API service
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
    app.secret_key = 'secret'
    port = int(os.environ['PORT'])
    app.run(debug=True, host='0.0.0.0', port = port)
