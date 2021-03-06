import gc
import multiprocessing
import time

import numpy as np

from openea.modules.finding.similarity import sim
from openea.modules.utils.util import task_divide, merge_dic


def greedy_alignment(embed1, embed2, top_k, nums_threads, metric, normalize, csls_k, accurate):
    """
    Search alignment with greedy strategy.

    Parameters
    ----------
    embed1 : matrix_like
        An embedding matrix of size n1*d, where n1 is the number of embeddings and d is the dimension.
    embed2 : matrix_like
        An embedding matrix of size n2*d, where n2 is the number of embeddings and d is the dimension.
    top_k : list of integers
        Hits@k metrics for evaluating results.
    nums_threads : int
        The number of threads used to search alignment.
    metric : string
        The distance metric to use. It can be 'cosine', 'euclidean' or 'inner'.
    normalize : bool, true or false.
        Whether to normalize the input embeddings.
    csls_k : int
        K value for csls. If k > 0, enhance the similarity by csls.

    Returns
    -------
    alignment_rest :  list, pairs of aligned entities
    hits1 : float, hits@1 values for alignment results
    mr : float, MR values for alignment results
    mrr : float, MRR values for alignment results
    """
    t = time.time()
    sim_mat = sim(embed1, embed2, metric=metric, normalize=normalize, csls_k=csls_k)
    num = sim_mat.shape[0]
    if nums_threads > 1:
        hits = [0] * len(top_k)
        ndcgs = np.array([0.0] * len(top_k), dtype=np.float)
        mr, mrr = 0, 0
        alignment_rest = set()
        rests = list()
        search_tasks = task_divide(np.array(range(num)), nums_threads)
        pool = multiprocessing.Pool(processes=len(search_tasks))
        for task in search_tasks:
            mat = sim_mat[task, :]
            rests.append(pool.apply_async(calculate_rank, (task, mat, top_k, accurate, num)))
        pool.close()
        pool.join()
        for rest in rests:
            sub_mr, sub_mrr, sub_hits, sub_hits1_rest, sub_ndcgs = rest.get()
            mr += sub_mr
            mrr += sub_mrr
            hits += np.array(sub_hits)
            alignment_rest |= sub_hits1_rest
            ndcgs += np.array(sub_ndcgs)
    else:
        mr, mrr, hits, alignment_rest, ndcgs = calculate_rank(list(range(num)), sim_mat, top_k, accurate, num)
    assert len(alignment_rest) == num
    hits = np.array(hits) / num * 100
    ndcgs = np.array(ndcgs) / num
    for i in range(len(hits)):
        hits[i] = round(hits[i], 3)
    cost = time.time() - t
    if accurate:
        if csls_k > 0:
            print("accurate results with csls: csls={}, hits@{} = {}%, ndcg@{} = {}, mr = {:.3f}, mrr = {:.6f}, time = {:.3f} s ".
                  format(csls_k, top_k, hits, top_k, ndcgs, mr, mrr, cost))
        else:
            print("accurate results: hits@{} = {}%, ndcg@{} = {}, mr = {:.3f}, mrr = {:.6f}, time = {:.3f} s ".
                  format(top_k, hits, top_k, ndcgs, mr, mrr, cost))
    else:
        if csls_k > 0:
            print("quick results with csls: csls={}, hits@{} = {}%, time = {:.3f} s ".format(csls_k, top_k, hits, cost))
        else:
            print("quick results: hits@{} = {}%, time = {:.3f} s ".format(top_k, hits, cost))
    hits1 = hits[0]
    del sim_mat
    gc.collect()
    return alignment_rest, hits1, mr, mrr


def greedy_alignment_exp(embed1, embed2, top_k, nums_threads, metric, normalize, csls_k, accurate):
    t = time.time()
    print("computing similarity")
    sim_mat = sim(embed1, embed2, metric=metric, normalize=normalize, csls_k=csls_k)
    num = sim_mat.shape[0]
    print("computing metrics")
    if nums_threads > 1:
        hits = [0] * len(top_k)
        ndcgs = [0] * len(top_k)
        mr, mrr = 0, 0
        alignment_rest = set()


        # rests = list()
        # search_tasks = task_divide(np.array(range(num)), nums_threads)
        # # multiple process
        # pool = multiprocessing.Pool(processes=len(search_tasks))
        # for task in search_tasks:
        #     mat = sim_mat[task, :]
        #     rests.append(pool.apply_async(calculate_rank, (task, mat, top_k, accurate, num)))
        # pool.close()
        # print("waiting for multiple process tasks to finish")
        # pool.join()

        # added by bing
        num_tasks = max(20, nums_threads)
        search_tasks = task_divide(np.array(range(num)), num_tasks)
        for idx in range(0, num_tasks, nums_threads):
            rests = list()
            pool = multiprocessing.Pool(processes=nums_threads)
            for task in search_tasks[idx: idx+nums_threads]:
                mat = sim_mat[task, :]
                rests.append(pool.apply_async(calculate_rank, (task, mat, top_k, accurate, num)))
            pool.close()
            print("waiting for multiple process tasks to finish")
            pool.join()
            for rest in rests:
                sub_mr, sub_mrr, sub_hits, sub_hits1_rest, sub_ndcgs = rest.get()
                mr += sub_mr
                mrr += sub_mrr
                hits += np.array(sub_hits)
                alignment_rest |= sub_hits1_rest
                ndcgs += np.array(sub_ndcgs)

    else:
        # mr, mrr, hits, alignment_rest, ndcgs = calculate_rank(list(range(num)), sim_mat, top_k, accurate, num)

        # single process
        hits = [0] * len(top_k)
        ndcgs = [0] * len(top_k)
        mr, mrr = 0, 0
        alignment_rest = set()
        rests = list()
        search_tasks = task_divide(np.array(range(num)), 20)
        for task in search_tasks:
            mat = sim_mat[task, :]
            res = calculate_rank(task, mat, top_k, accurate, num)
            # rests.append(res)

        # for rest in rests:
        #     sub_mr, sub_mrr, sub_hits, sub_hits1_rest, sub_ndcgs = rest
            sub_mr, sub_mrr, sub_hits, sub_hits1_rest, sub_ndcgs = res
            mr += sub_mr
            mrr += sub_mrr
            hits += np.array(sub_hits)
            alignment_rest |= sub_hits1_rest
            ndcgs += np.array(sub_ndcgs)


    assert len(alignment_rest) == num
    hits = np.array(hits) / num * 100
    ndcgs = np.array(ndcgs) / num
    for i in range(len(hits)):
        hits[i] = round(hits[i], 3)
    cost = time.time() - t
    if accurate:
        if csls_k > 0:
            print("accurate results with csls: csls={}, hits@{} = {}%, ndcg@{} = {}, mr = {:.3f}, mrr = {:.6f}, time = {:.3f} s ".
                  format(csls_k, top_k, hits, top_k, ndcgs, mr, mrr, cost))
        else:
            print("accurate results: hits@{} = {}%, ndcg@{} = {}, mr = {:.3f}, mrr = {:.6f}, time = {:.3f} s ".
                  format(top_k, hits, top_k, ndcgs, mr, mrr, cost))
    else:
        if csls_k > 0:
            print("quick results with csls: csls={}, hits@{} = {}%, time = {:.3f} s ".format(csls_k, top_k, hits, cost))
        else:
            print("quick results: hits@{} = {}%, time = {:.3f} s ".format(top_k, hits, cost))
    del sim_mat
    gc.collect()
    return alignment_rest, hits, mr, mrr, ndcgs



def stable_alignment(embed1, embed2, metric, normalize, csls_k, nums_threads, cut=100, sim_mat=None):
    t = time.time()
    if sim_mat is None:
        sim_mat = sim(embed1, embed2, metric=metric, normalize=normalize, csls_k=csls_k)

    kg1_candidates, kg2_candidates = dict(), dict()

    num = sim_mat.shape[0]
    x_tasks = task_divide(np.array(range(num)), nums_threads)
    pool = multiprocessing.Pool(processes=len(x_tasks))
    rests = list()
    total = 0
    for task in x_tasks:
        total += len(task)
        mat = sim_mat[task, :]
        rests.append(pool.apply_async(arg_sort, (task, mat, 'x_', 'y_')))
    assert total == num
    pool.close()
    pool.join()
    for rest in rests:
        kg1_candidates = merge_dic(kg1_candidates, rest.get())

    sim_mat = sim_mat.T
    num = sim_mat.shape[0]
    y_tasks = task_divide(np.array(range(num)), nums_threads)
    pool = multiprocessing.Pool(processes=len(y_tasks))
    rests = list()
    for task in y_tasks:
        mat = sim_mat[task, :]
        rests.append(pool.apply_async(arg_sort, (task, mat, 'y_', 'x_')))
    pool.close()
    pool.join()
    for rest in rests:
        kg2_candidates = merge_dic(kg2_candidates, rest.get())

    # print("kg1_candidates", len(kg1_candidates))
    # print("kg2_candidates", len(kg2_candidates))

    print("generating candidate lists costs time {:.3f} s ".format(time.time() - t))
    t = time.time()
    matching = galeshapley(kg1_candidates, kg2_candidates, cut)
    n = 0
    for i, j in matching.items():
        if int(i.split('_')[-1]) == int(j.split('_')[-1]):
            n += 1
    cost = time.time() - t
    print("stable alignment precision = {:.3f}%, time = {:.3f} s ".format(n / len(matching) * 100, cost))


def arg_sort(idx, sim_mat, prefix1, prefix2):
    candidates = dict()
    for i in range(len(idx)):
        x_i = prefix1 + str(idx[i])
        rank = (-sim_mat[i, :]).argsort()
        y_j = [prefix2 + str(r) for r in rank]
        candidates[x_i] = y_j
    return candidates


def calculate_rank(idx, sim_mat, top_k, accurate, total_num):
    assert 1 in top_k
    mr = 0
    mrr = 0
    hits = [0] * len(top_k)
    ndcgs = [0] * len(top_k)
    hits1_rest = set()
    for i in range(len(idx)):
        gold = idx[i]
        if accurate:
            rank = (-sim_mat[i, :]).argsort()
        else:
            rank = np.argpartition(-sim_mat[i, :], np.array(top_k) - 1)
        hits1_rest.add((gold, rank[0]))
        assert gold in rank
        rank_index = np.where(rank == gold)[0][0]
        mr += (rank_index + 1)
        mrr += 1 / (rank_index + 1)
        for j in range(len(top_k)):
            if rank_index < top_k[j]:
                hits[j] += 1
                ndcgs[j] += 1/np.log2(rank_index + 2)
    mr /= total_num
    mrr /= total_num
    return mr, mrr, hits, hits1_rest, ndcgs


def galeshapley(suitor_pref_dict, reviewer_pref_dict, max_iteration):
    """ The Gale-Shapley algorithm. This is known to provide a unique, stable
    suitor-optimal matching. The algorithm is as follows:

    (1) Assign all suitors and reviewers to be unmatched.

    (2) Take any unmatched suitor, s, and their most preferred reviewer, r.
            - If r is unmatched, match s to r.
            - Else, if r is matched, consider their current partner, r_partner.
                - If r prefers s to r_partner, unmatch r_partner from r and
                  match s to r.
                - Else, leave s unmatched and remove r from their preference
                  list.
    (3) Go to (2) until all suitors are matched, then end.

    Parameters
    ----------
    suitor_pref_dict : dict
        A dictionary with suitors as keys and their respective preference lists
        as values
    reviewer_pref_dict : dict
        A dictionary with reviewers as keys and their respective preference
        lists as values
    max_iteration : int
        An integer as the maximum iterations

    Returns
    -------
    matching : dict
        The suitor-optimal (stable) matching with suitors as keys and the
        reviewer they are matched with as values
    """
    suitors = list(suitor_pref_dict.keys())
    matching = dict()
    rev_matching = dict()

    for i in range(max_iteration):
        if len(suitors) <= 0:
            break
        for s in suitors:
            r = suitor_pref_dict[s][0]
            if r not in matching.values():
                matching[s] = r
                rev_matching[r] = s
            else:
                r_partner = rev_matching.get(r)
                if reviewer_pref_dict[r].index(s) < reviewer_pref_dict[r].index(r_partner):
                    del matching[r_partner]
                    matching[s] = r
                    rev_matching[r] = s
                else:
                    suitor_pref_dict[s].remove(r)
        suitors = list(set(suitor_pref_dict.keys()) - set(matching.keys()))
    return matching
