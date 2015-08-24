#!/usr/bin/env python2
"""Methods for dealing with our sound making thingies."""
from mingus.containers.note import Note
from mingus.containers.track import Track
from mingus.containers.composition import Composition
from mingus.containers.instrument import MidiInstrument
from mingus.midi import Sequencer

import time
import wave
import os
import subprocess
import fluidsynth as fs

SOUNDFONT = "FluidR3_GM.sf2"
OUTPUT = "pulseaudio"

class FluidSynthSequencer(Sequencer):

    """A simple MidiSequencer for FluidSynth.
    Modified slightly from Mingus's to suit our nefarious porpoises."""

    def init(self):
        self.fsynth = fs.Synth()
    
    def close(self):
        """Closes the synth."""
        self.fsynth.delete()
    
    def start_audio_output(self, driver=None):
        """Start the audio output.

        The optional driver argument can be any of 'alsa', 'oss', 'jack',
        'portaudio', 'sndmgr', 'coreaudio', 'Direct Sound', 'dsound',
        'pulseaudio'. Not all drivers will be available for every platform.
        """
        self.fsynth.start(driver)

    def start_recording(self, filename='mingus_dump.wav'):
        """Initialize a new wave file for recording."""
        wavfile = wave.open(filename, 'wb')
        wavfile.setnchannels(2)
        wavfile.setsampwidth(2)
        wavfile.setframerate(44100)
        self.wav = wavfile

    def load_sound_font(self, sf2):
        """Load a sound font.

        Return True on success, False on failure.

        This function should be called before your audio can be played,
        since the instruments are kept in the sf2 file.
        """
        self.sfid = self.fsynth.sfload(sf2)
        return not self.sfid == -1

    # Implement Sequencer's interface
    def play_event(self, note, channel, velocity):
        self.fsynth.noteon(channel, note, velocity)

    def stop_event(self, note, channel):
        self.fsynth.noteoff(channel, note)

    def cc_event(self, channel, control, value):
        self.fsynth.cc(channel, control, value)

    def instr_event(self, channel, instr, bank):
        self.fsynth.program_select(channel, self.sfid, bank, instr)
    
    def write_wav(self, seconds):
        """Forces a write of a 'seconds' long wav."""
        if hasattr(self, 'wav'):
            samples = self.fsynth.get_samples(int(seconds * 44100))
            audio = fs.raw_audio_string(samples)
            self.wav.writeframes(''.join(audio))

    def sleep(self, seconds):
        if hasattr(self, 'wav'):
            samples = fs.raw_audio_string(self.fsynth.get_samples(
                int(seconds * 44100)))
            self.wav.writeframes(''.join(samples))
        else:
            time.sleep(seconds)

def init_synth(font, driver = None, filename = None):
    """Initializes a new FluidsynthSequencer with the given driver or file"""
    seq = FluidSynthSequencer()
    if filename is not None:
        seq.start_recording(filename)
    else:
        seq.start_audio_output(driver)
    if not seq.load_sound_font(font):
        raise Exception("Can't find soundfont file: {0}".format(font))
    seq.fsynth.program_reset()
    return seq
        
def base88_encode(num):
    """Convert a number into a list of decimal numbers 0-87, or basically a
    base-88 number.
    Modified from http://stackoverflow.com/a/1119769"""
    if (num == 0):
        return [0]
    arr = []
    while num:
        rem = num % 88
        num = num // 88
        arr.append(rem)
    arr.reverse()
    return arr

def screen_to_track(user):
    """Returns a mingus NoteContainer generated from 
    the screenname of a person"""
    user_id = user.idnumber
    id_88 = base88_encode(user_id)
    out_track = Track()
    for i in id_88: 
        out_track.add_notes(Note().from_int(i))
    return out_track

def words_to_track(words):
    """Converts a string to a track, based on the the unicode code point, as
    given by ord()"""
    words_88 = [base88_encode(ord(x)) for x in words]
    notes = [Note().from_int(x) for letter in words_88 for x in letter]
    out_track = Track()
    for i in notes: 
        out_track.add_notes(i)
    return out_track

def sum_tracks(tracks):
    new_track = Track()
    for track in tracks:
        for bar in track:
            new_track.add_bar(bar)
    return new_track

def extend_track(track, length):
    """Repeats the bars of a track until it reaches the given length."""
    new_track = Track()
    while len(new_track) < length:
        for i in track:
            new_track.add_bar(i)
            if len(new_track) == length:
                return new_track
    return new_track

def composificate(tracks1, tracks2):
    """Extends tracks1 (presumed to be some sort of percussion) to the length of
    track2. Returns a Composition."""
    compo = Composition()
    #Extend each track1 to the length of the corresponding track2
    ntracks = []
    if len(tracks1) < len(tracks2):
        for track in tracks1:
            idx = tracks1.index(track)
            track = extend_track(track, len(tracks2[idx]))
            ntracks.append(track)
    else:
        ntracks = tracks1
    percus = sum_tracks(ntracks)
    melody = sum_tracks(tracks2)

    piano = MidiInstrument()
    piano.name = 'Acoustic Grand Piano'
    percussion = MidiInstrument()
    percussion.name = 'Woodblock'
    
    percus.instrument = percussion
    melody.instrument = piano
    compo.add_track(percus)
    compo.add_track(melody)
    return compo

def mp3ificate(composition, filename = "dump.wav"):
    """Creates an mp3 of a composition using subprocess and lame -f."""
    syn = init_synth(SOUNDFONT, filename = filename)
    syn.play_Composition(composition)
    syn.close()
    lame = subprocess.call(["lame", "-f", filename])
    oggenc = subprocess.call(["oggenc", "-q 1", filename])
    if lame is 0 and oggenc is 0: #if lame and oggenc returns normal
        os.remove(filename)
    return (lame, oggenc)
