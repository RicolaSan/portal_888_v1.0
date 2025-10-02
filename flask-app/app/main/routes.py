from flask import render_template, jsonify, request
from . import main

@main.route('/')
def index():
    return render_template('base.html')


