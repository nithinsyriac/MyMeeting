# import libraries
import os
from flask import Flask, render_template, request, redirect, session
import boto3
from boto3.dynamodb.conditions import Key, Attr
import requests
import json

# Initialize Flask app
application = Flask(__name__)
application.secret_key = "secret key"
app=application
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'


dynamodb = boto3.resource('dynamodb')
loginTable = dynamodb.Table('login')
MeetingTable = dynamodb.Table('Meeting')

s3 = boto3.resource('s3')
bucket_name_to_upload_image_to = 's3793275-assignment3'
AWS_S3_ENDPOINT = "s3-ap-southeast-2.amazonaws.com"


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', error = "")
    elif request.method == 'POST':
        email_id = request.form["email"]
        password = request.form["password"]
        user_details = check_user(email_id)
        if not(user_details) or (user_details[0]["password"] != password):
            error_message = "invalid credentials"
            return render_template('login.html', error = error_message)
        session["email_id"] = email_id
        session["username"] = user_details[0]["user_name"]
        return redirect("/main")


@app.route('/searchMeeting', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html', error = "")
    elif "email_id" in session:
        error_message = ""
        if request.method == 'POST':
            location = request.form["location"]
            if (location == "" ):
                error_message = "Please enter a Location.."
                response = ""
            else:
                response = search_meeting(location)
                if len(response) < 1:
                    error_message = "No results Found"
            return render_template("searchResult.html", message = error_message, meetings = response, username=session["username"])
            
def search_meeting(location):
        data = {
            'FilterExpression' :  Attr('location').begins_with(location) & Attr('sort_key').begins_with("TITLE-")
        }
        search_lst = []
        done = False
        start_key = None
        while not done:
            if start_key:
                data['ExclusiveStartKey'] = start_key
            response = MeetingTable.scan(**data)
            search_lst += (response.get('Items', []))
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return search_lst
    
@app.route('/displayMeetings')
def displayMeetings():
    if "email_id" in session:
        my_meetings = meetings_query(session["email_id"])
        if len(my_meetings) < 1:
            error_message = "You haven't joined to any meetings yet.."
            return render_template('joinedMeetings.html', username=session["username"], message=error_message)
        else:
            return render_template('joinedMeetings.html', username=session["username"],meetings = my_meetings)


@app.route('/createdMeetings')
def createdMeetings():
    if "email_id" in session:
        my_meetings = created_meetings_query(session["email_id"])
        if len(my_meetings) < 1:
            error_message = "You haven't created any meetings yet.."
            return render_template('createdMeetings.html', username=session["username"], message=error_message)
        else:
            return render_template('createdMeetings.html', username=session["username"],meetings = my_meetings)


def created_meetings_query(email):
    response = MeetingTable.query(
        KeyConditionExpression=Key('partition_key').eq("USER-"+email) & Key('sort_key').begins_with("TITLE-")
    )
    return response['Items']


@app.route('/addMeeting', methods=['GET', 'POST'])
def addMeeting():
    if request.method == 'GET':
        return render_template('addMeeting.html')
    elif request.method == 'POST':
        url = 'https://ed7328j11j.execute-api.ap-southeast-2.amazonaws.com/default/addMeeting'
        # email=session["email_id"]
        # title=request.form["title"]
        # location=request.form["location"]  
        # dateTime=request.form["date"] 
        # limit=request.form["limit"]

        # img = request.files["meeting_image"]
        # if not img:
        #     uploaded_image_url = "https://s3793275-assignment3.s3.ap-southeast-2.amazonaws.com/default.jpg"
        # else:
        #     req_data = img.read()
        #     filename = (request.files['meeting_image'].filename).replace(' ', '_')
        #     s3.Bucket(bucket_name_to_upload_image_to).put_object(Key=filename, Body=req_data)
        #     uploaded_image_url = 'https://%s.%s/%s' % (bucket_name_to_upload_image_to, AWS_S3_ENDPOINT, filename)
        # addMeeting_to_db(email,title,location,dateTime,limit,uploaded_image_url)

        data = {}
        data["email"] = "USER-"+session["email_id"]
        data["title"] = "TITLE-"+request.form["title"]
        data["location"] = request.form["location"]
        data["dateTime"] = request.form["date"]
        data["limit"] = request.form["limit"]
        data["username"] = session["username"]
        img = request.files["meeting_image"]

        if not img:
            uploaded_image_url = "https://s3793275-assignment3.s3.ap-southeast-2.amazonaws.com/default.jpg"
        else:
            req_data = img.read()
            filename = (request.files['meeting_image'].filename).replace(' ', '_')
            s3.Bucket(bucket_name_to_upload_image_to).put_object(Key=filename, Body=req_data)
            uploaded_image_url = 'https://%s.%s/%s' % (bucket_name_to_upload_image_to, AWS_S3_ENDPOINT, filename)
        data["img_url"] = uploaded_image_url
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        x = requests.post(url, data=json.dumps(data), headers=headers)
        return redirect("/main")



def addMeeting_to_db(email,title,location,dateTime,limit, uploaded_image_url):
    response = MeetingTable.put_item(
         Item={
            'partition_key': "USER-"+email,
            'sort_key': "TITLE-"+title,
            'location': location,
            'dateTime': dateTime,
            'limit' : limit,
            'username' : session["username"],
            'img_url' : uploaded_image_url
        }                  
    )
    return response


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', error = "")
    elif request.method == 'POST':
        email_id = request.form["email"]
        username = request.form["user_name"]
        password = request.form["password"]
        if(check_user(email_id)):
            error_message = "The Email id exists !!"
            return render_template('register.html', error = error_message)
        else:
            insert_user_login(email_id, password, username)
            return redirect('login')


@app.route('/main')
def main():
    if "email_id" in session:
        if request.method == 'GET':
            return render_template('main.html', username=session["username"])
        elif request.method == 'POST':
            return render_template('main.html', username=session["username"])
    else:
        return redirect('login')


@app.route('/join', methods=['POST'])
def join():
    if "email_id" in session:
        if request.method == 'POST':
            user = request.form["user"]
            host = request.form["join_host"]

            join_title = request.form["join_title"]
            if(user == session["username"]):
                return render_template(".html", message = "cannot join your own meeting", username=session["username"])
            else:
                joinMeeting(host, join_title)
                return redirect('main')
    else:
        return redirect('login')

def joinMeeting(email, title):
    url = "https://b9b7mbbx3e.execute-api.ap-southeast-2.amazonaws.com/default/joinMeeting"
    data = {}
    data["hostemail"] = email
    data["title"] = title
    data["email_id"] = session["email_id"]

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return response


def meetings_query(email):
    response = MeetingTable.query(
        KeyConditionExpression=Key('partition_key').eq("USER-"+email) & Key('sort_key').begins_with("JOIN-")
    )
    return response['Items']


def insert_user_login(email_id, password, username):
    response = loginTable.put_item(
       Item={
            'email': email_id,
            'user_name': username,
            'password': password
        }
    )
    return response

def check_user(email_id):
    response = loginTable.query(
        KeyConditionExpression=Key('email').eq(email_id)
    )
    return response['Items']

@app.route('/logout')
def logout():
    session.pop("email_id", None)
    session.pop("username", None)
    return redirect('login')


if __name__ == "__main__":
    app.run(debug=True) 