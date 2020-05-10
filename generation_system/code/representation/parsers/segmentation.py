#!/usr/bin/env python3.7
"""
This script presents the necessary functions for dealing with segmentation of musical phrases
"""

import math

import numpy as np

import representation.utils as utils


def change_degree(event_1, event_2):
    """
    Returns degree of change between two events for each feature
    of event
    """
    return [abs(a - b)/(a + b) if a != b else 0 for a, b in zip(event_1, event_2)]


def strength(nf_im1, nf_i, nf_ip1):
    """
    Gets Strength for each feature of an event from the its 
    normalized feature list representation,
    and the normalized feature list 
    representations of the previous and posterious events
    """
    degree_1 = change_degree(nf_im1, nf_i)
    degree_2 = change_degree(nf_i, nf_ip1)
    sum_nf = [a+b for a, b in zip(degree_1, degree_2)]
    return [a*b for a, b in zip(nf_i, sum_nf)]


def threshold_peak_picking(i, window, k, boundary_strengths):
    """
    Calculates the threshold value, using standard deviation and mean 
    In a specific Window of Time
    """
    start = 0
    if (i-window) > start:
        start = (i-window)

    bs_window = boundary_strengths[start:i]
    xbar = [sum(bs)/len(bs_window) for bs in zip(*bs_window)]
    deviations = [[(a - b)**2 for a, b in zip(bs, xbar)]
                  for bs in boundary_strengths[:i]]

    sum_dev = [sum(dev) for dev in zip(*deviations)]
    sum_mean = [sum(bs) for bs in zip(*boundary_strengths[:i])]

    variances = [math.sqrt(dev/(i-1)) for dev in sum_dev]
    means = [(mean/(i-1)) for mean in sum_mean]

    return [(k*v + m) for v, m in zip(variances, means)]


def peak_picking(i, boundary_strengths, weights, window=None, k=1.28):
    """
    Peak Picking Boundary Location Witten and Pearce

    Principles:
    - Note following a boundary should have greater/equal strength than following note
    - Note following a boundary should have greater/equal strength than preciding note
    - Note following a boundary should have higher (> k) strength

    Returns 1 for existent boundary before note
    Returns 0 for not existent boundary before note
    """
    if i < 2:  # First note is always a note following a boundary
        return 1-i  # Second note is not a candidate
    if i == len(boundary_strengths)-1:  # Penultimate note is not candidate
        return 0

    if window is None:
        window = i

    w_bs_i = np.dot(boundary_strengths[i], weights)
    w_bs_ip1 = np.dot(boundary_strengths[i+1], weights)
    w_bs_im1 = np.dot(boundary_strengths[i-1], weights)
    w_value = np.dot(threshold_peak_picking(
        i, window, k, boundary_strengths), weights)

    if (w_bs_i >= w_bs_ip1 and w_bs_i >= w_bs_im1 and w_bs_i > w_value):
        return 1
    return 0


def segmentation(events, weights_line=None, vertical_events=None, weights_vert=None, indexes=None):
    """
    Segmentation for a set of events, using 
    Peak Picking Boundary Location by Witten and Pearce
    """
    # with different weights
    if weights_line is None:
        weights_line = {  # candidates for phrasing discovery (melodic)
            'pitch.cpitch': 1,
            'rest': 1,
            'fermata': 1,
            'breath_mark': 1,
            'closure': 1,
        }

    # Get all events as a set of normalized features
    norm_features, _, _, weights = utils.create_feature_array_events(
        events, weights=weights_line, normalization='from_0',
        offset=False, flatten=False)

    norm_final_features = norm_features
    final_weights = weights

    if vertical_events is not None and indexes is not None:
        if weights_vert is None:
            weights_vert = {  # candidates for phrasing discovery (harmonic)
                'basic.root': 1,
                'pitches': 1,
                'cardinality': 1,
                'quality': 1,
                'prime_form': 1,
                'inversion': 1,
                'pitch_class': 1,
                'forte_class': 1,
                'pc_ordered': 1,
                'keysig': 1,
                'signatures.function': 1,
                'measure.function': 1,
            }

        normed_vert_features, _, _, weights_vert = utils.create_feature_array_events(
            vertical_events, weights=weights_vert, normalization='from_0',
            offset=False, flatten=False)

        for i, ind in enumerate(indexes):
            norm_final_features[i] = np.concatenate((norm_final_features[i], normed_vert_features[ind]))
            
        final_weights = np.concatenate((final_weights, weights_vert))

    # Calculate boundary strengths
    boundary_strengths = [strength(norm_final_features[i-1],
                                   norm_final_features[i], norm_final_features[i+1])
                          for i, _ in enumerate(events[1:-1])]
    boundary_strengths.insert(0, np.zeros(len(final_weights)))

    # Normalize strenghs and weights
    normalized_bss = utils.normalize(np.array(boundary_strengths), 0, 1)
    normalized_weights = utils.normalize_weights(final_weights)

    # Apply phrasing
    for i, event in enumerate(events):
        if i == len(events) - 1:
            events[-1].add_viewpoint('phrase.boundary', -1)
            break

        # Calculate presence of boundary
        boundary = peak_picking(i, normalized_bss, final_weights)
        event.add_viewpoint('phrase.boundary', boundary)
        if boundary == 1 and i != 0:
            events[i-1].add_viewpoint('phrase.boundary', -boundary)


def apply_segmentation_info(events):
    """
    """
    #print('Parse Segmentation')
    boundary_indexes = [
        i for i, event in enumerate(events) if event.get_viewpoint('pharse.boundary') == 1]

    for k, event in enumerate(events):
        if k != 0:
            index = boundary_indexes.index(
                min(boundary_indexes, key=lambda x: abs(x - k)))
            last_index = (
                index, index-1)[bool(k < boundary_indexes[index])]

            length = len(events) - boundary_indexes[last_index]
            if last_index < len(boundary_indexes)-1:
                length = boundary_indexes[last_index +
                                          1] - boundary_indexes[last_index]

            if k in boundary_indexes:
                last_index = boundary_indexes.index(k)-1
                length = len(events) - k
                if last_index < len(boundary_indexes)-2:
                    length = boundary_indexes[last_index+2] - k

            event.add_viewpoint('intphrase',  utils.seq_int(
                event.get_viewpoint('pitch.cpitch'), events[last_index].get_viewpoint('pitch.cpitch')))
            event.add_viewpoint('phrase.length', length)


def get_phrases_from_events(events, return_rest_phrases=False):
    """
    """
    phrase_begins = [i for i, event in enumerate(
        events) if event.get_viewpoint('pharse.boundary') == 1]

    phrases = []
    for i, begin in enumerate(phrase_begins):
        if i < len(phrase_begins) - 1:
            phrases.append(events[begin:phrase_begins[i+1]+1])
        else:
            phrases.append(events[begin:])

    if not return_rest_phrases:
        new_phrases = []
        for phrase in phrases:
            rests_of_phrase = [event for event in phrase if event.is_rest()]
            if len(rests_of_phrase) != len(phrase):
                new_phrases.append(phrase)
        phrases = new_phrases

    return phrases
