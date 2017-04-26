__author__ = 'ubriela'
import math
import logging
import time
import sys
import random
import numpy as np
import copy

import scipy.stats as stats
from Metrics import KLDivergence, RMSE, formatRes
from Utils import samplingUsers, transformDict, threshold, entropy, CEps2Str, noisyEntropy, noisyCount, noisyPoint, round2Grid, distance, euclideanToRadian, perturbedPoint
from LEBounds import globalSensitivy, localSensitivity, precomputeSmoothSensitivity, getSmoothSensitivity
from Differential import Differential
from LEStats import cellId2Coord, coord2CellId
from multiprocessing import Pool
from Kd_standard import Kd_standard
from Quad_standard import Quad_standard
from LEStats import readCheckins
from KExp import KExp

from Params import Params
from collections import defaultdict, Counter

sys.path.append('/Users/ubriela/Dropbox/_USC/_Research/_Crowdsourcing/_Privacy/PSD/src/icde12')

eps_list = [0.1, 0.5, 1.0, 5.0, 10.0]

seed_list = [9110, 4064, 6903]
# seed_list = [9110, 4064, 6903, 7509, 5342, 3230, 3584, 7019, 3564, 6456]

# C_list = [1]
C_list = [1,2,3,4,5,6,7,8,9,10]
# C_list = [1,5,10,15,20,15,30,35,40,45]

# [21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40
M_list = [1,2,3,4,5,6,7,8,9,10]

K_list = [10,20,30,40,50,60,70,80,90,100]


def actualEntropy(locs):
    """
    Compute actual shannon entropy from a set of locations
    :param locs:
    :return:
    """
    return dict([(lid, entropy(freqs.values())) for lid, freqs in locs.iteritems()])

def normalizeEntropy(e):
    # return max(0, e)
    return abs(e)
"""
Smoooth sensitivity
"""
def evalSS(p, E_actual):
    logging.info("evalSS")
    exp_name = "evalSS"
    methodList = [KLDivergence, RMSE]

    res_cube = np.zeros((len(eps_list), len(seed_list), len(methodList)))

    sampledUsers = samplingUsers(p.users, p.M)   # truncate M: keep the first M locations' visits
    locs = transformDict(sampledUsers)

    for j in range(len(seed_list)):
        for i in range(len(eps_list)):
            p.seed = seed_list[j]
            p.eps = eps_list[i]

            # smooth sensitivity
            ss = getSmoothSensitivity([p.C], [p.eps])
            ssList = [v * 2 for v in ss[CEps2Str(p.C, p.eps)]]

            E_noisy = defaultdict()
            for lid, counter in locs.iteritems():
                if len(counter) >= 1:
                    limitFreqs = threshold(counter.values(), p.C)
                    print len(ssList), len(limitFreqs)
                    smoothSens = ssList[min(len(limitFreqs) - 1, len(ssList) - 1)]
                    E_noisy[lid] = normalizeEntropy(noisyEntropy(entropy(limitFreqs), smoothSens, p.eps, p.seed)) #

            actual, noisy = [], []
            for lid, e in E_actual.iteritems():
                actual.append(e)
                noisy.append(E_noisy.get(lid, Params.DEFAULT_ENTROPY))   # default entropy = 0
            for k in range(len(methodList)):
                res_cube[i, j, k] = methodList[k](actual, noisy)

    res_summary = np.average(res_cube, axis=1)
    # res_summary_str = np.insert(res_summary.astype(str), 0, methodList, axis=0)
    np.savetxt(p.resdir + p.DATASET + "_" + exp_name + "_eps" + str(p.eps) + '_C' + str(p.C), res_summary, header="\t".join([f.__name__ for f in methodList]), fmt='%.4f\t')

"""
Add noise to each frequency
"""
def evalBL(p, E_actual):
    logging.info("evalBL")
    exp_name = "evalBL"
    methodList = [KLDivergence, RMSE]

    res_cube = np.zeros((len(eps_list), len(seed_list), len(methodList)))

    sampledUsers = samplingUsers(p.users, p.M)   # truncate M: keep the first M locations' visits
    locs = transformDict(sampledUsers)

    for j in range(len(seed_list)):
        for i in range(len(eps_list)):
            p.seed = seed_list[j]
            p.eps = eps_list[i]

            sensitivity = p.C * p.M

            E_noisy = defaultdict()
            for lid, counter in locs.iteritems():
                if len(counter) >= 1:
                    limitFreqs = threshold(counter.values(), p.C)  # thresholding
                    noisyFreqs = [noisyCount(freq, sensitivity, p.eps, p.seed) for freq in limitFreqs]
                    E_noisy[lid] = entropy([abs(f) for f in noisyFreqs]) # freq >= 0

            actual, noisy = [], []
            for lid, e in E_actual.iteritems():
                actual.append(e)
                noisy.append(E_noisy.get(lid, Params.DEFAULT_ENTROPY))   # default entropy = 0
            for k in range(len(methodList)):
                res_cube[i, j, k] = methodList[k](actual, noisy)

    res_summary = np.average(res_cube, axis=1)
    np.savetxt(p.resdir + p.DATASET + "_" + exp_name + "_eps" + str(p.eps) + '_C' + str(p.C), res_summary, header="\t".join([f.__name__ for f in methodList]), fmt='%.4f\t')


"""
Add 2d Laplace noise to each location
"""
def evalGeoI(p, E_actual):
    logging.info("evalGeoI")
    exp_name = "evalGeoI"
    methodList = [KLDivergence, RMSE]

    res_cube = np.zeros((len(eps_list), len(seed_list), len(methodList)))

    sampledUsers = samplingUsers(p.users, p.M)   # truncate M: keep the first M locations' visits
    locs = transformDict(sampledUsers)
    noisyLocs = defaultdict(Counter)

    for j in range(len(seed_list)):
        for i in range(len(eps_list)):
            p.seed = seed_list[j]
            p.eps = eps_list[i]

            E_noisy = defaultdict()
            for lid, counter in locs.iteritems():
                if len(counter) >= 1:
                    cellCoord = cellId2Coord(lid, p)

                    # randomly move this point a number of times
                    for uid, freq in counter.iteritems():
                        pp = perturbedPoint(cellCoord, p)
                        cellId = coord2CellId(pp, p)
                        noisyLocs[cellId].update([uid])

            actual, noisy = [], []
            cellIds = E_actual.keys() + noisyLocs.keys()
            for cellId in cellIds:
                actual.append(E_actual.get(cellId, Params.DEFAULT_ENTROPY))
                noisy.append(E_noisy.get(lid, Params.DEFAULT_ENTROPY))   # default entropy = 0
            for k in range(len(methodList)):
                res_cube[i, j, k] = methodList[k](actual, noisy)

    res_summary = np.average(res_cube, axis=1)
    np.savetxt(p.resdir + p.DATASET + "_" + exp_name + "_eps" + str(p.eps) + '_C' + str(p.C), res_summary, header="\t".join([f.__name__ for f in methodList]), fmt='%.4f\t')


def testDifferential():
    p = Params(1000)
    p.select_dataset()
    differ = Differential(1000)
    # RTH = (34.020412, -118.289936)
    TS = (40.758890, -73.985100)
    for i in range(100):
        (x, y) = differ.getTwoPlanarNoise(p.radius, p.eps)
        pp = noisyPoint(TS, (x,y))
        u = distance(p.x_min, p.y_min, p.x_max, p.y_min) * 1000.0 / Params.GRID_SIZE
        v = distance(p.x_min, p.y_min, p.x_min, p.y_max) * 1000.0 / Params.GRID_SIZE
        rad = euclideanToRadian((u, v))
        cell_size = np.array([rad[0], rad[1]])
        roundedPoint = round2Grid(pp, cell_size, p.x_min, p.y_min)
        # print (str(pp[0]) + ',' + str(pp[1]))
        print (str(roundedPoint[0]) + ',' + str(roundedPoint[1]))

testDifferential()