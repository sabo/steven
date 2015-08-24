import mongoengine as mge
import random
import poetry
import os

from db_tools import User, Poem
from werkzeug import SharedDataMiddleware
from flask import Flask, request, session, g, redirect, url_for, \
    abort, render_template
from wtforms import Form, TextField, BooleanField

DATABASE = 'twitter-poetry'

class PoetryRequest(Form):
    username_request = TextField('Username')
    haiku = BooleanField('Haiku?')
    friends = BooleanField('Traverse friend tree?')

app = Flask(__name__)
app.config.from_object(__name__)
mge.connect(DATABASE)

def connect_db():
    mge.connect(DATABASE)

def make_haiku(user, friends):
    if friends:
        pgen = poetry.haiku
    else:
        pgen = poetry.haiku_nofriends
    poem = pgen(user)
    poem.friends = friends
    poem.save()
    return poem

def make_stanza(user, friends):
    length = random.randint(1,15)
    lines = random.randint(1,7)
    if friends:
        pgen = poetry.stanza
    else:
        pgen = poetry.stanza_nofriends
    poem = pgen(user, length, lines)
    poem.friends = friends
    poem.save()
    return poem

@app.route('/', methods=['GET', 'POST'])
def request_poem():
    form = PoetryRequest(request.form)
    if request.method == 'POST':
        victim_list = User.objects(username = form.username_request.data)
        traverse = form.friends.data
        if victim_list:
            victim = victim_list[0]
        else:
            victim = random.choice(User.objects)
        if form.haiku.data:
            poem = make_haiku(victim, traverse)
        else:
            poem = make_stanza(victim, traverse)
        return redirect("/poems/{0}".format(poem.poem_id))
    return render_template('request.html', form=form)

@app.route('/poems/<int:p_id>')
def display_poem(p_id):
    poem = Poem.objects(poem_id = p_id)[0]
    return render_template('poem.html', poem = poem)   
if __name__ == '__main__':
    app.run()
