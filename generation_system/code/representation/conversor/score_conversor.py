#!/usr/bin/env python3.7
"""
This script presents the class ScoreConverter that converts the events
Generated by the System to a score
"""

import os

import music21

import representation.utils as utils


class ScoreConversor:
    """
    A class used to parse a musical file.

    Attributes
    ----------
    """

    def __init__(self):
        self.stream = music21.stream.Stream()
        self.last_voice_id = 0

    def parse_events(self, events, new_part=True, new_voice=True):
        """
        """
        stream = self.stream
        if new_part:
            self.last_voice_id = 0
            stream = music21.stream.Part()

        voice = music21.stream.Voice(id=self.last_voice_id)

        measures = []

        slurs = []

        bar_duration = music21.duration.Duration(quarterLength=4)
        last_key_signature = 0
        last_time_signature = ''
        last_metro_value = ''
        last_instrument = music21.instrument.Instrument('')
        last_dynamics = []

        for event in events:
            if new_voice and event.get_viewpoint('fib') and len(measures) > 0:
                # measures[-1].makeNotation(inPlace=True)
                measures[-1].append(voice)
                voice = music21.stream.Voice(id=self.last_voice_id)
            if (len(measures) == 0 or event.get_viewpoint('fib')
                    or measures[-1].barDurationProportion(barDuration=bar_duration) == 1.0):
                # measures[-1].makeNotation(inPlace=True)
                measures.append(music21.stream.Measure())

            instrument = event.get_viewpoint('instrument')
            if instrument is None:
                instrument = music21.instrument.Instrument()
            if instrument != last_instrument and not isinstance(instrument, str):
                stream.append(instrument)
                last_instrument = instrument

            keysig = event.get_viewpoint('keysig')
            if keysig != last_key_signature:
                stream.append(music21.key.KeySignature(
                    sharps=int(keysig)))
                last_key_signature = keysig

            time_sig = event.get_viewpoint('timesig')
            if time_sig != last_time_signature:
                time_signature = music21.meter.TimeSignature(time_sig)
                stream.append(time_signature)
                last_time_signature = time_sig
                bar_duration = time_signature.barDuration

            metro_value = event.get_viewpoint('metro.value')
            if metro_value != last_metro_value:
                stream.append(
                    music21.tempo.MetronomeMark(
                        text=event.get_viewpoint('metro.text'),
                        number=metro_value,
                        referent=music21.note.Note(type=event.get_viewpoint('ref.type'))))
                last_metro_value = metro_value

            note = None
            if event.is_rest():
                note = music21.note.Rest(
                    quarterLength=event.get_viewpoint('duration.length'),
                    type=event.get_viewpoint('duration.type'),
                    dots=event.get_viewpoint('duration.dots'))
            else:
                note = self.convert_note_event(event)

            if new_voice:
                voice.append(note)
            else:
                measures[-1].append(note)

            for dyn in event.get_viewpoint('dynamic'):
                if not dyn in last_dynamics:
                    measures[-1].insert(stream.highestOffset,
                                        music21.dynamics.Dynamic(dyn))
            last_dynamics = event.get_viewpoint('dynamic')

            if event.get_viewpoint('slur.begin'):
                slurs.append(music21.spanner.Slur())
                pass

        if events[0].get_viewpoint('posinbar') > 0:
            measures[0].padAsAnacrusis(useGaps=False, useInitialRests=True)

        if new_voice and len(measures) > 0:
            measures[-1].append(voice)

        if self.last_voice_id == 0:
            stream.append(measures)
        else:
            for i, measure in enumerate(list(stream.recurse(classFilter='Measure'))):
                for v in measures[i].voices:
                    measure.append(v)

        #music21.stream.makeNotation.makeMeasures(stream, inPlace=True, searchContext=True)

        if new_voice:
            self.last_voice_id += 1
        if new_part:
            self.stream.append(stream)

        return self.stream

    def convert_note_event(self, event):
        """
        Convert Note Event
        """
        pitch = music21.pitch.Pitch(event.get_viewpoint(
            'dnote') + str(int(event.get_viewpoint('octave'))))

        if event.get_viewpoint('accidental') is not music21.pitch.Accidental('natural').modifier:
            acc = music21.pitch.Accidental('natural')
            acc.modifier = event.get_viewpoint('accidental')
            pitch.accidental = acc

        if pitch.ps != event.get_viewpoint('cpitch'):
            pitch.ps = event.get_viewpoint('cpitch')

        note = music21.note.Note(
            pitch, quarterLength=event.get_viewpoint('duration.length'),
            type=event.get_viewpoint('duration.type'),
            dots=event.get_viewpoint('duration.dots'))

        if event.is_chord():
            note = music21.chord.Chord([music21.pitch.Pitch(p) for p in event.get_viewpoint(
                'chordPitches')],
                quarterLength=event.get_viewpoint(
                'duration.length'),
                type=event.get_viewpoint(
                'duration.type'),
                dots=event.get_viewpoint('duration.dots'))

        for articulation in event.get_viewpoint('articulation'):
            note.articulations.append(
                getattr(music21.articulations, articulation.capitalize())())

        if event.get_viewpoint('breath mark'):
            note.articulations.append(music21.articulations.BreathMark())

        for exp in event.get_viewpoint('expression'):
            note.expressions.append(
                getattr(music21.expressions, exp.capitalize())())

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

        if event.is_grace_note():
            note.getGrace(appogiatura=True, inPlace=True)

        return note
