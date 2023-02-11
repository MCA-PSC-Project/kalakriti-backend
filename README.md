# kalakriti-backend
backend api for kalakriti app

## windows

### one time

`python -m venv .venv`

`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`


### always execute once (when opening vs code)

`.\.venv\Scripts\activate`

## linux

`python3 -m venv .venv`

`source .venv/bin/activate`

## for installing required python packages

`pip install -r requirements.txt`

## launch flask web server

`flask run`

### launch flask web server without autoreloading

`flask run --no-reload`

### Flask app start on port number
`flask run --port=5001`