#!/usr/bin/env python3.7
"""
This script defines the generation algorithm for synchronization of various Oracles
"""

import random

import numpy as np

from generation.oracles.factor_oracle import FactorOracle


def sync_generate(oracles, offsets, seq_len=10, p=0.5, k=1):
    """
    Generate synchronized lines from various oracles
    """
    len_events_by_part = [(key, len(part)) for key, part in offsets.items()]
    len_events_by_part.sort(key=lambda tup: tup[1], reverse=True)
    principal_key = len_events_by_part[0][0]
    max_size = len_events_by_part[0][1] + 1

    trns = {}
    sfxs = {}
    lrss = {}
    rsfxs = {}
    sequences = {}
    ktraces = {}

    for key, oracle in oracles.items():
        trns[key] = oracle.basic_attributes['trn'][:]
        sfxs[key] = oracle.basic_attributes['sfx'][:]
        lrss[key] = oracle.basic_attributes['lrs'][:]
        rsfxs[key] = oracle.basic_attributes['rsfx'][:]
        sequences[key] = []
        ktraces[key] = [k]

    for _i in range(seq_len):
        ks_at_offset_k = _find_ks(offsets, principal_key, k)

        # generate each state
        if sfxs[principal_key][k] != 0 and sfxs[principal_key][k] is not None:
            if (random.random() < p):
                # copy forward according to transitions
                I = trns[principal_key][k]
                if len(I) == 0:
                    # if last state, choose a suffix
                    k = sfxs[principal_key][k]
                    ktraces[principal_key].append(k)
                    I = trns[principal_key][k]
                sym = I[int(np.floor(random.random() * len(I)))]
                new_ks = _find_ks(offsets, principal_key, sym)
                _ = [sequences[key].append(value) for key, value in new_ks.items()]
                _ = [ktraces[key].append(value) for key, value in ks_at_offset_k.items()]
                k = sym
            else:
                # copy any of the next symbols
                _ = [ktraces[key].append(value) for key, value in ks_at_offset_k.items()]
                k_vecs = dict([(key, []) for key in sfxs.keys()])
                k_vecs = dict([(key, _find_links(k_vecs[key], sfxs[key], rsfxs[key], ks_at_offset_k[key]))
                               for key in ks_at_offset_k.keys()])
                lrs_vecs = dict([(key, [lrss[key][_i] for _i in k_vec]) for key, k_vec in k_vecs.items()])
                sym = get_max_lrs_position(
                    k_vecs, lrs_vecs, max_size)

                k_symbols = _find_ks(offsets, principal_key, sym)
                if sym == len(sfxs[principal_key]) - 1:
                        sym = sfxs[principal_key][sym] + 1
                else:
                    _ = [sequences[key].append(ks + 1) for key, ks in k_symbols.items()]
                
                k = sym + 1
                _ = [ktraces[key].append(ks + 1) for key, ks in k_symbols.items()]
        else:
            if k < len(sfxs[principal_key]) - 1:
                # copy forward
                for key, ks in ks_at_offset_k.items():
                    sequences[key].append(ks + 1)
                    ktraces[key].append(ks + 1)
                k += 1
            else:
                sym = sfxs[principal_key][k] + 1
                for key, ks in _find_ks(offsets, principal_key, sym).items():
                    sequences[key].append(ks + 1)
                    ktraces[key].append(ks + 1)
                k = sym

        if k > len(sfxs[principal_key]) - 1:
            k = 0

    return sequences, ktraces

def get_max_lrs_position(k_vecs, lrs_vecs, length):
    """
    """
    max_lrss = [0] * length
    for key, k_vec in k_vecs.items():
        for i, k in enumerate(k_vec):
            if lrs_vecs[key][i] > max_lrss[k]:
                max_lrss[k] = lrs_vecs[key][i]
    return max_lrss.index(max(max_lrss))

def _find_ks(offsets, principal_key, k):
    """
    Find k for parts at offset x
    """
    return dict([(key, off.index(offsets[principal_key][k-1])+1) for key, off in offsets.items() if offsets[principal_key][k-1] in off])


def _find_links(k_vec, sfx, rsfx, k):
    """Find sfx/rsfx recursively."""
    k_vec.sort()
    if 0 in k_vec:
        return k_vec
    else:
        if sfx[k] not in k_vec:
            k_vec.append(sfx[k])
        for i in range(len(rsfx[k])):
            if rsfx[k][i] not in k_vec:
                k_vec.append(rsfx[k][i])
        for i in range(len(k_vec)):
            k_vec = _find_links(k_vec, sfx, rsfx, k_vec[i])
            if 0 in k_vec:
                break
        return k_vec


""" 
trn_k = dict([(key, trn[ktraces[key][-1]])
                      for key, trn in trns.items()])
        sfx_k = dict([(key, sfx[ktraces[key][-1]])
                      for key, sfx in sfxs.items()])
        lrs_k = dict([(key, lrs[ktraces[key][-1]])
                      for key, lrs in lrss.items()])
        rsfxs_k = dict([(key, rsfx[ktraces[key][-1]])
                        for key, rsfx in rsfxs.items()])

        if all(sfx_k[oracle] != 0 and sfx_k[oracle] is not None for oracle in oracles.keys()):
            if (random.random() < p):
                # copy forward according to transitions
                for oracle in oracles.keys():
                    if len(trn_k[oracle]) == 0:  # TODO: sync
                        # if last state, choose a suffix
                        k = sfx_k[oracle]
                        ktrace.append(k)
                        trn_k[oracle] = trns[oracle][k]
                    # TODO: sync
                    sym = trn_k[oracle][int(
                        np.floor(random.random() * len(trn_k[oracle])))]
                    sequences[oracle].append(sym)
                    ktraces[oracle].append(sym)
            else:
                # copy any of the next symbols
                for oracle in oracles.keys():
                    ktraces[oracle].append(ktraces[oracle][-1])
                    k_vec = []
                    k_vec = _find_links(
                        k_vec, sfxs[oracle], rsfxs[oracle], ktraces[oracle][-1])
                    k_vec = [_i for _i in k_vec if lrss[oracle][_i] >= LRS]
                    lrs_vec = [lrss[oracle][_i] for _i in k_vec]
                    if len(k_vec) > 0:  # if a possibility found, len(I)
                        if weight == 'weight':
                            max_lrs = np.amax(lrs_vec)
                            query_lrs = max_lrs - np.floor(random.expovariate(1))

                            if query_lrs in lrs_vec:
                                _tmp = np.where(lrs_vec == query_lrs)[0]
                                _tmp = _tmp[int(
                                    np.floor(random.random() * len(_tmp)))]
                                sym = k_vec[_tmp]
                            else:
                                _tmp = np.argmin(abs(
                                    np.subtract(lrs_vec, query_lrs)))
                                sym = k_vec[_tmp]
                        elif weight == 'max':
                            sym = k_vec[np.argmax([lrss[oracle][_i]
                                                for _i in k_vec])]
                        else:
                            sym = k_vec[int(
                                np.floor(random.random() * len(k_vec)))]

                    
                        if sym == len(sfxs[oracle]) - 1:
                            sym = sfxs[oracle][sym] + 1
                        else:
                            sequences[oracle].append(sym + 1)
                        ktraces[oracle].append(sym + 1)
                    else:  # otherwise continue
                        if ktraces[oracle][-1] < len(sfxs[oracle]) - 1:
                            sym = ktraces[oracle][-1] + 1
                        else:
                            sym = sfx_k[oracle] + 1
                        sequences[oracle].append(sym)
                        ktraces[oracle].append(sym)

        else:
            for oracle in oracles.keys():
                k = ktraces[oracle][-1]
                if k < len(sfxs[oracle]) - 1:
                    sequences[oracle].append(k + 1)
                    ktraces[oracle].append(k + 1)
                else:
                    sym = sfx_k[oracle] + 1
                    sequences[oracle].append(sym)
                    ktraces[oracle].append(sym)

        for oracle in oracles.keys():
            if ktraces[oracle][-1] >= len(sfxs[oracle]) - 1:
                ktraces[oracle][-1] = 0 
"""