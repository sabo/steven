import mongoengine as mge
import random
import re
import music
import murmur
from db_tools import User, Poem
from hyphen import Hyphenator

hy = Hyphenator()

def generate_syllable_chain(syllables, markov):
    out = []
    word = random.choice(markov.keys())
    #Three-letter words and smaller are one syllable.
    #I HAVE SPOKEN.
    if len(word) < 4:
        syllable_count = 1
    else:
        syllable_count = len(hy.syllables(unicode(word)))
    out.append(word)
    while syllable_count < syllables:
        try:
            step = random.choice(markov[word])
        except KeyError:
            #Try again.
            out = generate_syllable_chain(syllables, markov)
            return out
        out.append(step)
        syl = len(hy.syllables(unicode(step)))
        if syl == 0:
            syllable_count += 1
        else:
            syllable_count += syl
        if syllable_count > syllables:
            #FUCKIT START OVER
            out = generate_syllable_chain(syllables, markov)
            return out
        word = step
    return out

def generate_chain(length, markov, strict = True):
    out = []
    word = random.choice(markov.keys())
    #We need to strip out any . and $ in order to work with mongo.
    out.append(word)
    while len(out) < length:
        try:
            step = random.choice(markov[word])
        except KeyError:
            if strict:
                #Restart
                out = generate_chain(length, markov, strict)
                return out
            else:
                return out
        out.append(step)
        word = step
    return out

def get_friend(user):
    """Returns a random user object from a list of friends."""
    friend = random.choice(user.friends)
    return User.objects(username = friend)[0]

def add_links(string):
    hashtag = "(?<=\#)\w+"
    username = "(?<=\@)\w+"
    tco = "(\://tco/)"
    bitly = "(\://bitly)"
    shortener_link = "<a href=\"{0}\">{0}</a>"
    username_link = "<a href=\"http://twitter.com/{0}\">{0}</a>"
    hashtag_link = "<a href=\"http://twitter.com/search?q={0}&src=hash\">{1}</a>"

def haiku(user):
    #Can't do users until we're closed under corpus
    out = []
    poem = Poem()
    poem.seed_user = user
    users = [user]
    for i in [5,7,5]:
        ln = ' '.join(generate_syllable_chain(i, user.corpus))
        out.append(ln)
        user = get_friend(user)
        users.append(user)

    idnumber = murmur.string_hash((u''.join(out)).encode('utf-8'))
    poem.lines = out
    poem.poem_id = idnumber

    percussion = [music.screen_to_track(u) for u in users]
    melody = [music.words_to_track(w) for w in out]
    composition = music.composificate(percussion, melody)
    filename = "audio/{0}.wav".format(str(idnumber))
    music.mp3ificate(composition, filename)
    
    poem.save()
    return poem 

def haiku_nofriends(user):
    """haiku for someone with no friends."""
    out = []
    poem = Poem()
    poem.seed_user = user

    for i in [5, 7, 5]:
        ln = ' '.join(generate_syllable_chain(i, user.corpus))
        out.append(ln)

    idnumber = murmur.string_hash((u''.join(out)).encode('utf-8'))
    poem.lines = out
    poem.poem_id = idnumber

    percussion = [music.screen_to_track(user)]
    melody = [music.words_to_track(w) for w in out]
    composition = music.composificate(percussion, melody)
    filename = "audio/{0}.wav".format(str(idnumber))
    music.mp3ificate(composition, filename)
    
    poem.save()
    return poem

def stanza_nofriends(user, max_length, lines):
    out = []
    poem = Poem()
    poem.seed_user = user
   
    for _ in range(lines):
        ln = ' '.join(generate_chain(length = max_length, 
                markov = user.corpus, 
                strict = False))
        out.append(ln)
        print ln
    
    idnumber = murmur.string_hash((u''.join(out)).encode('utf-8'))
    poem.lines = out
    poem.poem_id = idnumber

    percussion = [music.screen_to_track(user)]
    melody = [music.words_to_track(w) for w in out]
    composition = music.composificate(percussion, melody)
    filename = "audio/{0}.wav".format(str(idnumber))
    music.mp3ificate(composition, filename)

    poem.save()
    return poem

def stanza(user, max_length, lines):
    out = []
    poem = Poem()
    poem.seed_user = user

    for _ in range(lines):
        ln = ' '.join(generate_chain(length = max_length, 
                markov = user.corpus,
                strict = False))
        out.append(ln)
        user = get_friend(user)
    
    idnumber = murmur.string_hash((u''.join(out)).encode('utf-8'))
    poem.poem_id = idnumber
    poem.lines = out

    percussion = [music.screen_to_track(user)]
    melody = [music.words_to_track(w) for w in out]
    composition = music.composificate(percussion, melody)
    filename = "audio/{0}.wav".format(str(idnumber))
    music.mp3ificate(composition, filename)
    
    poem.save()
    return poem
