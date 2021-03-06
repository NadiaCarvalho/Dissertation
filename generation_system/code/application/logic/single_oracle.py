"""
Single part Oracle and Sequence Generator
"""
import os
import time
import random
import numpy as np

import application.logic.generation.gen_algorithms.generation as gen
import application.logic.generation.plot_fo as gen_plot
import application.logic.generation.utils as gen_utils
from application.logic.generation.cdist_fixed import distance_between_windowed_features
from application.logic.representation.conversor.score_conversor import parse_single_line, parse_single_interpart
from application.logic.representation.events.linear_event import PartEvent
from application.logic.representation.events.interpart_event import InterPartEvent
from application.logic.representation.parsers.utils import get_last_x_events_that_are_notes_before_index


def get_single_part_features(application, information, line):
    """
    Get Part Features
    """
    normed_features = []
    original_features = []

    line_splitted = '.'.split(line)
    for music, _tuple in application.music.items():
        parser = _tuple[0]

        i = 0
        for key, events in parser.get_part_events().items():
            if len(events) > 0 and any(k in line_splitted for k in '.'.split(key)):
                # Get Start and End Indexes
                start_index = application.indexes_first[music]['parts'][i]
                finish_index = start_index + len(events)

                normed_features.extend(
                    information['selected_normed'][start_index:finish_index])
                original_features.extend(
                    information['selected_original'][start_index:finish_index])
                break
            elif len(events) > 0:
                i += 1

    return normed_features, original_features


def get_inter_part_features(application, information):
    """
    Get Inter-Part Features
    """
    normed_features = []
    original_features = []

    for music, _tuple in application.music.items():
        parser = _tuple[0]
        interpart_events = parser.get_interpart_events()

        if len(interpart_events) > 0:
            start_index = application.indexes_first[music]['inter-part']
            finish_index = start_index + len(interpart_events)

            normed_features.extend(
                information['selected_normed'][start_index:finish_index])
            original_features.extend(
                information['selected_original'][start_index:finish_index])

    return normed_features, original_features


def line_extraction(application, line):
    if 'inter-part' not in line:
        part_information = application.music_information['parts']
        features_names = part_information['selected_features_names']
        weights = part_information['normed_weights']
        fixed_weights = part_information['fixed_weights']

        # Get Normed and Original Features
        normed_features, original_features = get_single_part_features(application,
                                                                      part_information, line)
    else:
        part_information = application.music_information['inter-part']
        features_names = part_information['selected_features_names']
        weights = part_information['normed_weights']
        fixed_weights = part_information['fixed_weights']

        # Get Normed and Original Features
        normed_features, original_features = get_inter_part_features(application,
                                                                     part_information)

    return normed_features, original_features, weights, fixed_weights, features_names


def construct_single_oracle(application, line):
    """
    Construct Oracle from Information
    """
    normed_features, original_features, weights, fixed_weights, features_names = line_extraction(
        application, line)

    thresh = gen_utils.find_threshold(
        _r=(0, 1, 0.1),
        input_data=normed_features, weights=weights,
        fixed_weights=fixed_weights,
        dim=len(features_names), entropy=True)

    oracle = gen_utils.build_oracle(
        normed_features, flag='a', features=features_names,
        weights=weights, fixed_weights=fixed_weights,
        dim=len(features_names), dfunc='cosine', threshold=thresh[0][1])

    # image = gen_plot.start_draw(oracle)
    # name = r'data\oracles\oracle' + '.PNG'
    # image.save(name)

    application.oracles_information['single_oracle'] = {
        'key': line,
        'oracle': oracle,
        'normed_features': normed_features,
        'original_features': original_features,
        'features_names': features_names,
        'weights': weights,
        'fixed_weights': fixed_weights,
        'threshold': thresh[0][1]
    }


def generate_sequences_single(information, num_seq):
    """
    Generate Sequences
    """
    ordered_sequences = []

    i = 0
    while i < num_seq:
        p = random.uniform(0, 1)
        lrs = int(random.uniform(
            1, max(information['oracle'].basic_attributes['lrs'])))

        sequence, kend, ktrace = gen.generate(
            oracle=information['oracle'], seq_len=50, p=p, k=-1, LRS=lrs)

        if len(sequence) > 0:
            dist = distance_between_windowed_features(
                [information['normed_features'][state-1]
                    for state in sequence],
                information['normed_features'])

            # calculate ktrace distance as
            # (#non-consecutive / #total-recuperaded-states)
            dist_2 = sum(np.diff(ktrace) != 1)/len(ktrace)

            ordered_sequences.append((sequence, dist, dist_2))
            i += 1

    ordered_sequences.sort(key=lambda tup: tup[2])
    return ordered_sequences


def generate_from_single(application, num_seq):
    """
    Generate Music From a Single Oracle
    """
    information = application.oracles_information['single_oracle']

    localtime = time.asctime(time.localtime(time.time()))
    localtime = '_'.join(localtime.split(' '))
    localtime = '-'.join(localtime.split(':'))

    original_sequence = range(len(information['original_features']))
    linear_score_generator(application, original_sequence,
                           information['original_features'],
                           information['features_names'],
                           name='original.xml', time='generations_' + localtime,
                           start=0, line=information['key'])

    ordered_sequences = generate_sequences_single(
        information, num_seq)
    # Generate Scores of Ordered Sequences
    for i, (sequence, dist_1, dist_2) in enumerate(ordered_sequences):
        name = 'gen_' + str(i) + '_distF_' + str(round(dist_1)) + \
            '_distC_' + str(round(dist_2, 2)) + '.xml'
        linear_score_generator(application, sequence,
                               information['original_features'],
                               information['features_names'],
                               name=name, time='generations_' + localtime, line=information['key'])


def linear_score_generator(application, sequence, o_information,
                           feature_names, name='',
                           time='', start=-1, line=''):
    """
    Score Generator for Single Line
    """
    if 'inter-part' not in line:
        sequenced_events = [PartEvent(
            from_list=o_information[state+start], features=feature_names) for state in sequence]

        if application.principal_music is not None:
            start_pitch = application.principal_music[0].get_part_events()[
                line][0].get_viewpoint('pitch')
            if start == -1:
                last_pitch_index = get_last_x_events_that_are_notes_before_index(
                    application.principal_music[0].get_part_events()[line],
                    number=1, actual_index=start)
                start_pitch = application.principal_music[0].get_part_events()[
                    line][last_pitch_index].get_viewpoint('pitch')
        else:
            start_pitch = o_information[start][feature_names.index('pitch.cpitch')]
    else:
        sequenced_events = [InterPartEvent(
            from_list=o_information[state+start], features=feature_names) for state in sequence]

    if len(sequenced_events) > 0:
        if 'inter-part' not in line:
            score = parse_single_line(
                sequenced_events, start_pitch=start_pitch)
        else:
            score = parse_single_interpart(sequenced_events)

        splitted_db = application.database_path.split(os.sep)
        if len(splitted_db) == 1:
            splitted_db = application.database_path.split('/')

        db_path = os.sep.join(splitted_db[:-1])
        gen_folder = os.sep.join([db_path, 'generations', time])
        if not os.path.exists(gen_folder):
            try:
                os.makedirs(gen_folder, exist_ok=True)
            except OSError:
                print("Creation of the directory %s failed" % gen_folder)
            else:
                print("Successfully created the directory %s " % gen_folder)
                path = os.sep.join([gen_folder, name + '.xml'])
                fp = score.write(fp=path)
        else:
            path = os.sep.join([gen_folder, name + '.xml'])
            fp = score.write(fp=path)
