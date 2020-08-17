"""
Olivia immunization functions.

Immunization analyzes in which packages it is better to invest to protect the network as a whole.
"""

import random

from olivia.lib.graphs import removed, strong_articulation_points
from olivia.model import OliviaNetwork
from olivia.networkmetrics import failure_vulnerability
from olivia.packagemetrics import Reach, DependentsCount, Impact, Surface


def immunization_delta(net, n, cost_metric=Reach):
    """
    Compute the improvement in network Phi vulnerability by immunizing a certain set of packages.

    Parameters
    ----------
    net: OliviaNetwork
        Input network.
    n: container
        Container of packages to be immunized.
    cost_metric: class, optional
        Metric to measure cost.

    Returns
    -------
    result: float, float, float
        Initial vulnerability, vulnerability after immunization, difference.

    Notes
    -----
    Implements the naive algorithm of removing immunized nodes and rebuilding model from scratch, so it is
    really slow for big networks. Some obvious improvements could be made, but whether or not there is a
    much better alternative is an open question.

    """
    f1 = failure_vulnerability(net, metric=cost_metric)
    size_correction = (len(net.network)-len(n))/len(net.network)
    with removed(net.network, n):
        immunized_net = OliviaNetwork()
        immunized_net.build_model(net.network)
        f2 = failure_vulnerability(immunized_net, metric=cost_metric)
    f2 = size_correction*f2
    return f1, f2, f1 - f2


def iset_naive_ranking(olivia_model, set_size, metric=Reach):
    """
    Compute an immunization set by selecting top elements according to a metric.

    Parameters
    ----------
    olivia_model: OliviaNetwork
        Input network
    set_size: int
        Number of packages in the immunization set.
    metric: class, optional
        Metric to measure cost.

    Returns
    -------
    immunization_set: set
        Set of packages to be immunized.

    """
    return {p[0] for p in olivia_model.get_metric(metric).top(set_size)}


def iset_delta_frame_reach(olivia_model):
    """
    Compute an immunization set using the DELTA FRAME algorithm with the Reach metric.

    DELTA FRAME computes upper and lower bounds for the vulnerability reduction associated to the immunization of
    each package in the network and returns a set that is guaranteed to contain the single optimum package for
    immunization.

    The resulting set size is a product of the algorithm and cannot be selected.

    Parameters
    ----------
    olivia_model: OliviaNetwork
        Input network

    Returns
    -------
    immunization_set: set
        Set of packages to be immunized.

    """
    delta_upper = olivia_model.get_metric(Reach) * olivia_model.get_metric(Surface)
    delta_lower = olivia_model.get_metric(Reach) + olivia_model.get_metric(Surface) - 1
    max_lower = delta_lower.top()[0][1]
    return {p for p in olivia_model if delta_upper[p] > max_lower}


def iset_delta_frame_impact(olivia_model):
    """
    Compute an immunization set using the DELTA FRAME algorithm with the Impact metric.

    DELTA FRAME computes upper and lower bounds for the vulnerability reduction associated to the immunization of
    each package in the network and returns a set that is guaranteed to contain the single optimum package for
    immunization.

    The resulting set size is a product of the algorithm and cannot be selected.

    Parameters
    ----------
    olivia_model: OliviaNetwork
        Input network

    Returns
    -------
    immunization_set: set
        Set of packages to be immunized.

    """
    delta_upper = olivia_model.get_metric(Impact) * olivia_model.get_metric(Surface)
    delta_lower = olivia_model.get_metric(DependentsCount) * olivia_model.get_metric(Surface)
    max_lower = delta_lower.top()[0][1]
    return {p for p in olivia_model if delta_upper[p] > max_lower}


def iset_sap(olivia_model, clusters=None):
    """
    Compute an immunization set detecting strong articulation points (SAP).

    Immunization of SAP in the strongly connected components (SCC) of the network can be very effective
    in networks with large SCCs.

    Large SCC play a crucial role in increasing the vulnerability of networks of dependencies. Strong articulation
    points are nodes whose removal would create additional strongly connected components, thus reducing the size of
    the larger SCC.

    The appearance of SCCs in real packet networks seems to follow a model similar to the formation of the giant
    component in Erdős-Rényi models. So the size of the largest SCC is usually much larger than the rest.

    The resulting set size is a product of the algorithm and cannot be selected.

    Parameters
    ----------
    olivia_model: OliviaNetwork
        Input network

    clusters: sets of nodes
        Iterable with sets of nodes forming SCCs in the network. If None the largest SCC is detected and used.

    Returns
    -------
    immunization_set: set
        Set of packages to be immunized corresponding to the SAP of the clusters.

    """
    if clusters is None:
        clusters = [olivia_model.sorted_clusters()[0]]
    sap = set()
    for c in clusters:
        scc = olivia_model.network.subgraph(c)
        sap.update(strong_articulation_points(scc))
    return sap


def iset_random(olivia_model, set_size, indirect=False, seed=None):
    """
    Compute an immunization set by randomly selecting packages.

    This method is useful for understanding the nature of a network's vulnerability and/or for
    establishing baseline immunization cases.

    Parameters
    ----------
    olivia_model: OliviaNetwork
        Input network
    set_size: int
        Number of packages in the immunization set.
    indirect: bool, optional
        Whether to use indirect selection or not. Using indirect selection the immunization set is constructed
        by randomly choosing a dependency of a randomly selected package.
    seed: int, optional
        Seed for the random number generator.

    Returns
    -------
    immunization_set: set
        Set of packages to be immunized.

    """
    packages = tuple(olivia_model)
    if seed:
        random.seed(seed)
    if indirect:
        result = set()
        while len(result) != set_size:
            dependencies = []
            while len(dependencies) == 0:
                current = random.choice(packages)
                dependencies = olivia_model[current].direct_dependencies()
            result.add(random.choice(tuple(dependencies)))
        return result
    else:
        return set(random.sample(packages, k=set_size))