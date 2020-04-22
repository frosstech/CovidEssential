from functools import wraps
import sys
import os
from flask import Flask, render_template, redirect, request, url_for, session
#coming from pyrebase4
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import folium
import requests


#firebase config
config = {
  "apiKey": "AIzaSyBiKO9FTo79jZk3bJO-GUOQhrCmgy2RDm8",
  "authDomain": "covidessentials-ff3b9.firebaseapp.com",
  "databaseURL": "https://covidessentials-ff3b9.firebaseio.com",
  "projectId": "covidessentials-ff3b9",
  "storageBucket": "covidessentials-ff3b9.appspot.com",
  "messagingSenderId": "997050913925",
  "appId": "1:997050913925:web:3b44c15795c08a7c30c5ec",
  "measurementId": "G-P8NL64W4X5"
}

#init firebase
firebase = pyrebase.initialize_app(config)
#auth instance
auth = firebase.auth()
#cloud firestore database instance
cred = credentials.Certificate("covidessentials-ff3b9-firebase-adminsdk-6zi28-4195f306af.json")
firebase_admin.initialize_app(cred)
db=firestore.client()

#new instance of Flask
app = Flask(__name__)
#secret key for the session
app.secret_key = os.urandom(24)

#getting the geo location
geo = requests.get('https://get.geojs.io/v1/ip.json')
my_ip = geo.json()['ip']
geo_request_url = 'https://get.geojs.io/v1/ip/geo/' + my_ip + '.json'
geo_request = requests.get(geo_request_url)
geo_data = geo_request.json()

#folium initialization
m = folium.Map(location=[geo_data['latitude'], geo_data['longitude']], zoom_start=10)

#tooltip
tooltip = 'Click here to HELP'

#overallPostIteration
def overAllPosts():
  # initializing python dictionary
  m = folium.Map(location=[geo_data['latitude'], geo_data['longitude']], zoom_start=10)
  emailDict={}
  postDict={}
  #getting every users email
  usersEmail=db.collection('usersemail').stream()
  for email in usersEmail:
    emailDict=email.to_dict()
    #getting every users posts
    emailsPost = db.collection('users').document(emailDict['email']).collection('posts').stream()
    for post in emailsPost:
      #getting each post
      postDict=post.to_dict()
      #marking location in the map
      print(postDict['latitude'],postDict['longitude'])
      folium.Marker([postDict['latitude'], postDict['longitude']],
               popup=('<strong>Name: </strong>' + str(postDict['name']).capitalize() + '<br>'
                      '<strong>Need: </strong>' + str(postDict['need']).upper() + '<br>'
                      '<strong>Phone: </strong>' + str(postDict['phone']) ),
               icon=folium.Icon(icon='plus-sign', color='green'),
               tooltip=tooltip).add_to(m)
      #print(postDict["need"],postDict['author'],postDict['name'],postDict['phone'],postDict['latitude'],postDict['longitude'])
  m.save('templates/map.html')

#updating the map 
overAllPosts()

#decorator to protect routes
def isAuthenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #check for the variable that pyrebase creates
        if not auth.current_user != None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

#home route
@app.route("/")
def home():
  return render_template("layout.html")

#index route
@app.route("/index")
@isAuthenticated
def index():
  
  docs = db.collection('users').document(session['email']).collection('posts').stream()
  posts={}
  for doc in docs:
    #print(u'{} => {}'.format(doc.id, doc.to_dict()))
    posts[doc.id]=doc.to_dict()
  if docs==None:
    return render_template("index.html")
  else:
    return render_template("index.html", posts=posts)

#signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
      #get the request form data
      email = request.form["email"]
      password = request.form["password"]
      try:
        #create the user
        auth.create_user_with_email_and_password(email, password)
        #login the user right away
        user = auth.sign_in_with_email_and_password(email, password)   
        #session
        user_id = user['idToken']
        user_email = email
        session['usr'] = user_id
        session["email"] = user_email
        db.collection("usersemail").document().set({
          "email": email,
        })
        return redirect("/index") 
      except:
        return render_template("login.html", message="The email is already taken, try another one, please" )  

    return render_template("signup.html")


#login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
      #get the request data
      email = request.form["email"]
      password = request.form["password"]
      try:
        #login the user
        user = auth.sign_in_with_email_and_password(email, password)
        #set the session
        user_id = user['idToken']
        user_email = email
        session['usr'] = user_id
        session["email"] = user_email
        return redirect("/index")  
      
      except:
        return render_template("login.html", message="Wrong Credentials" )  

     
    return render_template("login.html")

#logout route
@app.route("/logout")
def logout():
    #remove the token setting the user to None
    auth.current_user = None
    #also remove the session
    session.clear()
    return redirect("/")

#create form
@app.route("/create", methods=["GET", "POST"])
@isAuthenticated
def create():
  if request.method == "POST":
    #get the request data
    name = request.form["name"]
    need = request.form["need"]
    phone=request.form["contact"]
    latitude = request.form["latitude"]
    longitude = request.form["longitude"]

    if latitude=="":
      latitude=geo_data['latitude']
    
    if longitude=="":
      longitude=geo_data['longitude']

    post = {
      "name": name,
      "need": need,
      "latitude": latitude,
      "longitude": longitude,
      "phone": phone,
      "author": session["email"]
    }

    #form validation
    if(len(name)>0 and len(need)>0 and len(phone)==10 and (need=="Water" or need=="Food" or need=="Medicine")):
      try:
        db.collection('users').document(session['email']).collection('posts').document().set(post)
        overAllPosts()
        return redirect("/index")
      except:
        return render_template("create.html", message= "Something wrong happened")
    else:
      return render_template("create.html", message= "* Every field must be filled and Phone number should be exactly 10 digit")
      

  return render_template("create.html")

#map route
@app.route("/map")
def map():

  return render_template("map.html")

#about route
@app.route("/about")
def about():
  return render_template("about.html")

#post
@app.route("/post/<id>")
@isAuthenticated
def post(id):
    orderedDict = db.collection('users').document(session['email']).collection('posts').document(id).get()
    doc={}
    doc[id]=orderedDict.to_dict()
    return render_template("post.html", data=doc)

#delete function
@app.route("/delete/<id>", methods=["GET"])
def delete(id):
    db.collection('users').document(session["email"]).collection("posts").document(id).delete()
    overAllPosts()
    return redirect("/index")


#run the main script
if __name__ == "__main__":
    app.run(debug=True)
