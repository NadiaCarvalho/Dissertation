#!/usr/bin/env python3.7
"""
This script presents the class ScoreConverter that converts the events
Generated by the System to a score
"""

import music21
import numpy as np

from application.representation.parsers.utils import \
    get_last_x_events_that_are_notes_before_index


def parse_multiple(event_dict, start_pitches=None):
    """
    Create Score from Multiple Events
    """
    parts = {}
    for key, events in event_dict.items():
        instrument_key = str(key).split('.')[0]

        start_pitch = 'C4'
        if start_pitches is not None and key in start_pitches:
            start_pitch = start_pitches[key]

        if '.' in key and instrument_key in parts:  # Voice and not part
            parts[instrument_key] = parse_single_line(
                events, stream=parts[instrument_key],
                voice_id=int(key.split('.')[1]), start_pitch=start_pitch, single=False)
        else:
            parts[instrument_key] = parse_single_line(
                events, start_pitch=start_pitch, single=False)

    to_shift = {}
    potential_anacrusis = dict([(key, events[0].get_viewpoint(
        'anacrusis')) for key, events in event_dict.items()])

    if any(value for value in potential_anacrusis.values()):
        posinbar = dict([(key, events[0].get_viewpoint('posinbar'))
                         for key, events in event_dict.items()])
        to_shift = posinbar

    stream = music21.stream.Stream()
    for key, part in parts.items():
        part.makeNotation(inPlace=True)

        if (key in to_shift and to_shift[key] > 0):
            part.shiftElements(to_shift[key])
            part.makeMeasures(inPlace=True)
            part.measure(1).padAsAnacrusis()

        stream.insert(0, part)

    return stream


def parse_single_line(events, stream=None, voice_id=0, start_pitch='C4', single=True):
    """
    Convert Single Line of events to stream
    """
    part = music21.stream.Part()
    bar_duration = music21.duration.Duration(quarterLength=4)
    last_key_signature = 0
    last_time_signature = ''
    last_metro_value = ''
    last_instrument = music21.instrument.Instrument()
    last_dynamics = []
    slurs = []

    if stream is not None:
        part = stream
        if len(stream.getElementsByClass('Measure')) > 0:
            bar_duration = stream.getElementsByClass('Measure')[0].barDuration
        if len(stream.getElementsByClass('KeySignature')) > 0:
            last_key_signature = stream.getElementsByClass('KeySignature')[
                0].sharps
        if len(stream.getElementsByClass('TimeSignature')) > 0:
            last_time_signature = str(
                stream.getElementsByClass('TimeSignature')[0])
        if len(stream.getElementsByClass('MetronomeMark')) > 0:
            last_metro_value = str(
                stream.getElementsByClass('MetronomeMark')[0])

        last_instrument = stream.getInstrument()

    voice = music21.stream.Voice(id=voice_id)
    last_offset = 0

    for i, event in enumerate(events):

        if isinstance(event, str):
            duration = event.split('_')[1]
            voice.append(music21.note.Rest(quarterLength=abs(float(duration))))
            last_offset = voice.highestTime
            continue

        last_instrument = instrument_selection(
            event, part, last_instrument, last_offset)
        last_key_signature = keysig_selection(
            event, voice, last_key_signature, last_offset)
        last_time_signature, bar_duration = timesig_selection(
            event, part, last_time_signature, bar_duration, last_offset)
        last_metro_value = metro_selection(
            event, part, last_metro_value, last_offset)

        for dyn in event.get_viewpoint('dynamic'):
            if dyn not in last_dynamics:
                voice.insert(last_offset,
                             music21.dynamics.Dynamic(dyn))
        last_dynamics = event.get_viewpoint('dynamic')

        last_pitch = start_pitch
        if len(voice.notes) > 0:
            if isinstance(voice.notes[-1], music21.note.Note):
                last_pitch = voice.notes[-1].nameWithOctave

        note = None
        if event.is_rest():
            note = music21.note.Rest(duration=duration_conversion(event))
        else:
            note = convert_note_event(event, last_pitch)

        note = articulation_conversion(event, note)
        note = expressions_conversion(event, note)
        voice.append(note)
        last_offset = voice.highestTime

    slur_conversor(voice, events)
    diminuendo_conversor(voice, events)
    crescendo_conversor(voice, events)

    part.insert(0, voice, ignoreSort=False)
    #part.show('text')

    if single:
        part.makeNotation(inPlace=True)

    return part


def slur_conversor(voice, events):
    """
    Slur Parsing
    """
    slurs = []
    note_or_rests = voice.flat.notesAndRests.stream()
    start_slurs = [(i, event) for i, event in enumerate(
        events) if not isinstance(event, str) and event.get_viewpoint('slur.begin')]
    for (i, start) in start_slurs:
        slurs.append(music21.spanner.Slur())
        start_note = note_or_rests[i]
        slurs[-1].addSpannedElements(start_note)

        for j, note in enumerate(note_or_rests.elements[i+1:]):
            if note not in slurs[-1].getSpannedElements():
                slurs[-1].addSpannedElements(note)
            if events[i+1+j].get_viewpoint('slur.end'):
                break

    for slur in slurs:
        voice.append(slur)


def diminuendo_conversor(voice, events):
    """
    Diminuendo Parsing
    """
    diminuendos = []
    note_or_rests = voice.flat.notesAndRests.stream()
    start_dim = [(i, event) for i, event in enumerate(events)
                 if not isinstance(event, str) and event.get_viewpoint('diminuendo.begin')]
    for (i, start) in start_dim:
        diminuendos.append(music21.dynamics.Diminuendo())
        start_note = note_or_rests[i]
        diminuendos[-1].addSpannedElements(start_note)

        for j, note in enumerate(note_or_rests.elements[i+1:]):
            if note not in diminuendos[-1].getSpannedElements():
                diminuendos[-1].addSpannedElements(note)
            if events[i+1+j].get_viewpoint('diminuendo.end'):
                break

    for diminuendo in diminuendos:
        voice.append(diminuendo)


def crescendo_conversor(voice, events):
    """
    Crescendo Parsing
    """
    crescendos = []
    note_or_rests = voice.flat.notesAndRests.stream()
    start_dim = [(i, event) for i, event in enumerate(events)
                 if not isinstance(event, str) and event.get_viewpoint('crescendo.begin')]
    for (i, start) in start_dim:
        crescendos.append(music21.dynamics.Crescendo())
        start_note = note_or_rests[i]
        crescendos[-1].addSpannedElements(start_note)

        for j, note in enumerate(note_or_rests.elements[i+1:]):
            if note not in crescendos[-1].getSpannedElements():
                crescendos[-1].addSpannedElements(note)
            if events[i+1+j].get_viewpoint('crescendo.end'):
                break

    for crescendo in crescendos:
        voice.append(crescendo)


def instrument_selection(event, stream, last_instrument, offset):
    """
    Renovates Instrument of Part/Voice if different from last
    """
    instrument = event.get_viewpoint('instrument')
    if instrument is None or isinstance(instrument, str):
        instrument = music21.instrument.Instrument()

    if str(instrument) != str(last_instrument):
        stream.insert(offset, instrument)
        last_instrument = instrument

    return last_instrument


def keysig_selection(event, stream, last_key_signature, offset):
    """
    Renovates Key Signature of Part/Voice if different from last
    """
    keysig = event.get_viewpoint('keysig')
    if keysig != last_key_signature:
        stream.insert(offset, music21.key.KeySignature(sharps=int(keysig)))
        last_key_signature = keysig

    return last_key_signature


def timesig_selection(event, stream, last_time_signature, bar_duration, offset):
    """
    """
    time_sig = event.get_viewpoint('timesig')
    if time_sig != last_time_signature:
        time_signature = music21.meter.TimeSignature(time_sig)
        stream.insert(offset, time_signature)
        last_time_signature = time_sig
        bar_duration = time_signature.barDuration
    return last_time_signature, bar_duration


def metro_selection(event, stream, last_metro_value, offset):
    metro_value = event.get_viewpoint('metro.value')
    if metro_value != last_metro_value:
        stream.insert(
            offset,
            music21.tempo.MetronomeMark(
                text=event.get_viewpoint('metro.text'),
                number=metro_value,
                referent=music21.note.Note(type=event.get_viewpoint('ref.type'))))
        last_metro_value = metro_value
    return last_metro_value


def convert_note_event(event, start_pitch):
    """
    Convert Note Event
    """
    if event.is_chord() and event.get_viewpoint('chordPitches') != []:
        note = music21.chord.Chord([music21.pitch.Pitch(p) for p in event.get_viewpoint(
            'chordPitches')], duration=duration_conversion(event))
    else:
        note = music21.note.Note(
            pitch_conversion(event, start_pitch), duration=duration_conversion(event))

    note.volume = event.get_viewpoint('volume')

    note.notehead = event.get_viewpoint('notehead.type')
    note.noteheadFill = event.get_viewpoint('notehead.fill')
    parenthesis = event.get_viewpoint('notehead.parenthesis')
    if parenthesis:
        note.noteheadParenthesis = parenthesis

    if event.is_grace_note():
        note.getGrace(appogiatura=True, inPlace=True)

    return note


def pitch_conversion(event, start_pitch):
    """
    Return Pitch of Event
    """
    pitch = music21.pitch.Pitch(start_pitch)

    if (event.get_viewpoint('dnote') is None
            and event.get_viewpoint('cpitch') is None):
        pitch.ps += event.get_viewpoint('seq_int')
        pitch.updateAccidentalDisplay()
    else:
        if (event.get_viewpoint('dnote') is not None):
            pitch = music21.pitch.Pitch(event.get_viewpoint(
                'dnote') + str(int(event.get_viewpoint('octave'))))

            if event.get_viewpoint('accidental') is not music21.pitch.Accidental('natural').modifier:
                acc = music21.pitch.Accidental('natural')
                acc.modifier = event.get_viewpoint('accidental')
                pitch.accidental = acc

        if (event.get_viewpoint('cpitch') is not None and
                pitch.ps != event.get_viewpoint('cpitch')):
            pitch.ps = event.get_viewpoint('cpitch')
            pitch.updateAccidentalDisplay()

    return pitch


def duration_conversion(event):
    """
    Return Pitch of Event
    """
    duration = music21.duration.Duration(quarterLength=event.get_viewpoint('duration.length'),
                                         type=event.get_viewpoint(
        'duration.type'),
        dots=event.get_viewpoint('duration.dots'))

    duration_1 = event.get_viewpoint('duration.length') % 1
    try:
        if (np.asscalar(duration_1) % 5 != 0.0
                or np.mod(event.get_viewpoint('duration.length'), 1) != 0):
            duration = music21.duration.Duration(
                quarterLength=event.get_viewpoint('duration.length'))
    except Exception:
        'No item'

    if event.get_viewpoint('duration.type') == '2048th':
        duration = music21.duration.Duration(
            quarterLength=event.get_viewpoint('duration.length'))

    return duration


def articulation_conversion(event, note):
    """
    Return note with articulations
    """
    for articulation in event.get_viewpoint('articulation'):
        note.articulations.append(
            getattr(music21.articulations, articulation.capitalize())())

    if event.get_viewpoint('breath mark'):
        note.articulations.append(music21.articulations.BreathMark())

    return note


def expressions_conversion(event, note):
    """
    Return note with expressions
    """
    for exp in event.get_viewpoint('expressions.expression'):
        try:
            note.expressions.append(
                getattr(music21.expressions, exp.capitalize())())
        except AttributeError:
            try:
                as_articulation = getattr(
                    music21.articulations, exp.capitalize())()
                if as_articulation not in note.articulations:
                    note.articulations.append(as_articulation)
            except AttributeError:
                print('Expression is not Expression or Articulation')

    for orn in event.get_viewpoint('ornamentation'):
        splitted = orn.split(':')
        ornament = getattr(music21.expressions, splitted[0].capitalize())()

        if splitted[0] == 'turn' or splitted[0] == 'appogiatura':
            ornament.name = splitted[1]
        elif splitted[0] == 'trill':
            ornament.placement = splitted[1]
            ornament.size.name = splitted[2]
        elif splitted[0] == 'tremolo':
            ornament.measured = splitted[1]
            ornament.numberOfMarks = splitted[2]
        elif splitted[0] == 'mordent':
            ornament.direction = splitted[1]
            ornament.size.name = splitted[2]

        note.expressions.append(ornament)

    if event.get_viewpoint('fermata'):
        note.expressions.append(music21.expressions.Fermata())

    if event.get_viewpoint('rehearsal'):
        note.expressions.append(music21.expressions.RehearsalMark())

    return note
