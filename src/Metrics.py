from Params import Params
from scipy import stats
import math
import numpy as np
# import editdistance
import collections
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score

def KLDivergence(P, Q):
    """
    Returns the KL divergence, K(P || Q) - the amount of information lost when Q is used to approximate P
    :param P:
    :param Q:
    :return:
    """
    divergence = 0.0
    sump, sumq = float(sum(P)), float(sum(Q))
    probP, probQ = [p/sump for p in P], [q/sumq for q in Q]

    for i in range(len(probP)):
        if probP[i] < Params.PRECISION or probQ[i] < Params.PRECISION: continue
        divergence += probP[i] * math.log(probP[i]/probQ[i], Params.base)
    return divergence

def KLDivergence2(pk, pq):
    return stats.entropy(pk, pq, Params.base)

def mse(actual, noisy):
    """
    Return mean square error
    :param actual:
    :param noisy:
    :return:
    """
    mean_squared_error(actual, noisy)

def rmse(actual, noisy):
    """
    Return root mean square error
    :param actual:
    :param noisy:
    :return:
    """
    return math.sqrt(mse(actual, noisy))

    # noisy_vals = []
    # actual_vals = []
    # print len(actual), actual
    # print len(noisy), noisy
    # for lid in noisy.keys():
    #     noisy_vals.append(noisy.get(lid))
    #     if not actual.has_key(lid):
    #         print lid
    #     actual_vals.append(actual.get(lid))

    # print len(actual_vals), actual_vals
    # print len(noisy_vals), noisy_vals

def mre(actual, noisy):
    """
    Return mean relative error
    :param actual:
    :param noisy:
    :return:
    """
    if len(actual) != len(noisy): return -1
    absErr = np.abs(np.array(actual) - np.array(noisy))
    idx_nonzero = np.where(np.array(actual) != 0)
    absErr_nonzero = absErr[idx_nonzero]
    true_nonzero = np.array(actual)[idx_nonzero]
    relErr = absErr_nonzero / true_nonzero
    return relErr.mean()

# noisy_vals, actual_vals = [], []
# for lid in noisy.keys():
#     noisy_vals.append(noisy.get(lid))
#     actual_vals.append(actual.get(lid))