
from numpy import matrix, identity, zeros
from itertools import chain, combinations

from IMCoalHMM.model import Model
from IMCoalHMM.state_spaces import CoalSystem
from IMCoalHMM.state_spaces import Isolation, make_rates_table_isolation
from IMCoalHMM.state_spaces import Single, make_rates_table_single
from IMCoalHMM.transitions import CTMCSystem, projection_matrix, compute_upto, compute_between
from IMCoalHMM.CTMC import make_ctmc
from IMCoalHMM.emissions import coalescence_points
from IMCoalHMM.break_points import uniform_break_points, exp_break_points


class Admixture(CoalSystem):
    """Class for IM system with exactly two samples."""

    def __init__(self):
        """Constructs the state space and collect B, L, R and E states (see the
        CoalHMM papers for what these are)."""

        super(Admixture, self).__init__()

        self.transitions = [[('R', self.recombination)], [('C', self.coalesce)]]

        # We need various combinations of initial states to make sure we build the full reachable state space.
        left_1 = [frozenset([(1, (frozenset([1]), frozenset([])))]), frozenset([(2, (frozenset([1]), frozenset([])))])]
        right_1 = [frozenset([(1, (frozenset([]), frozenset([1])))]), frozenset([(2, (frozenset([]), frozenset([1])))])]
        left_2 = [frozenset([(1, (frozenset([2]), frozenset([])))]), frozenset([(2, (frozenset([2]), frozenset([])))])]
        right_2 = [frozenset([(1, (frozenset([]), frozenset([2])))]), frozenset([(2, (frozenset([]), frozenset([2])))])]
        self.init = [l1 | r1 | l2 | r2 for l1 in left_1 for r1 in right_1 for l2 in left_2 for r2 in right_2]

        self.compute_state_space()


def make_rates_table_admixture(coal_rate_1, coal_rate_2, recomb_rate):
    """Builds the rates table from the CTMC for the two-samples system
    for an isolation period."""
    table = dict()
    table[('C', 1, 1)] = coal_rate_1
    table[('C', 2, 2)] = coal_rate_2
    table[('R', 1, 1)] = recomb_rate
    table[('R', 2, 2)] = recomb_rate
    return table


## Helper functions
def powerset(iterable):
    """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return set(chain.from_iterable(combinations(s, r) for r in range(len(s)+1)))


def complement(universe, subset):
    """Extract universe \ subset."""
    return set(universe).difference(subset)


def population_lineages(population, lineages):
    return set((p, lineage) for p, lineage in lineages if p == population)


def outer_product(set1, set2):
    for x in set1:
        for y in set2:
            yield x, y


## Output for debugging... makes the states easier to read
def pretty_state(state):
    """Presents a coalescence system state in an easier to read format."""
    def pretty_set(s):
        if len(s) == 0:
            return "{}"
        else:
            return "{{{}}}".format(','.join(str(x) for x in s))

    def lineage_map(lin):
        p, (l, r) = lin
        return "[{}, ({},{})]".format(p, pretty_set(l), pretty_set(r))

    return " ".join(map(lineage_map, state))


def admixture_state_space_map(from_space, to_space, p, q):
    """Constructs the mapping matrix from the 'from_space' state space to the 'to_space' state space
    assuming an admixture event where lineages in population 0 moves to population 1 with probability p
    and lineages in population 1 moves to population 0 with probability q."""
    destination_map = to_space.state_numbers
    map_matrix = matrix(zeros((len(from_space.states), len(to_space.states))))

    for state, from_index in from_space.state_numbers.items():
        population_1 = population_lineages(1, state)
        population_2 = population_lineages(2, state)

        # <debug>
        #print pretty_state(state)
        # </debug>
        total_prob = 0.0

        for x, y in outer_product(powerset(population_1), powerset(population_2)):
            cx = complement(population_1, x)
            cy = complement(population_2, y)

            ## Keep x and y in their respective population but move the other two...
            cx = frozenset((2, lin) for (p, lin) in cx)
            cy = frozenset((1, lin) for (p, lin) in cy)

            destination_state = frozenset(x).union(cx).union(y).union(cy)
            change_probability = p**len(cx) * (1.0 - p)**len(x) * q**len(cy) * (1.0 - q)**len(y)
            to_index = destination_map[destination_state]

            # <debug>
            #print '->', pretty_state(destination_state),
            #print "p^{} (1-p)^{} q^{} (1-q)^{}".format(len(cx), len(x), len(cy), len(y))
            #print from_index, '->', to_index, '[{}]'.format(change_probability)
            # </debug>

            map_matrix[from_index, to_index] = change_probability
            total_prob += change_probability

        # <debug>
        #print
        #print total_prob
        # </debug>

        # We want to move to another state with exactly probability 1.0
        assert abs(total_prob - 1.0) < 1e-10

    return map_matrix




# FIXME: add initial state as an option to have three configurations: 11, 12, and 22
class AdmixtureCTMCSystem12(CTMCSystem):
    """Wrapper around CTMC transition matrices for the isolation model."""

    def __init__(self, isolation_ctmc, middle_ctmc, ancestral_ctmc,
                 p, q, middle_break_points, ancestral_break_points):
        """Construct all the matrices and cache them for the
        method calls.
        """

        super(AdmixtureCTMCSystem12, self).__init__(no_hmm_states=len(middle_break_points) + len(ancestral_break_points),
                                                    initial_ctmc_state=isolation_ctmc.state_space.i12_index)

        self.no_middle_states = len(middle_break_points)
        self.middle = middle_ctmc
        self.no_ancestral_states = len(ancestral_break_points)
        self.ancestral = ancestral_ctmc

        self.through_ = [None] * (self.no_middle_states + self.no_ancestral_states - 1)

        for i in xrange(self.no_middle_states - 1):
            self.through_[i] = middle_ctmc.probability_matrix(middle_break_points[i+1] - middle_break_points[i])

        xx = middle_ctmc.probability_matrix(ancestral_break_points[0] - middle_break_points[-1])
        projection = projection_matrix(middle_ctmc.state_space, ancestral_ctmc.state_space,
                                       lambda state: frozenset([(0, nucs) for (_, nucs) in state]))
        self.through_[self.no_middle_states - 1] = xx * projection

        for i in xrange(self.no_middle_states, self.no_middle_states + self.no_ancestral_states - 1):
            ii = i - self.no_middle_states
            self.through_[i] = ancestral_ctmc.probability_matrix(ancestral_break_points[ii+1] - ancestral_break_points[ii])

        pseudo_through = matrix(zeros((len(ancestral_ctmc.state_space.states), len(ancestral_ctmc.state_space.states))))
        pseudo_through[:, ancestral_ctmc.state_space.end_states[0]] = 1.0
        self.through_.append(pseudo_through)

        projection = admixture_state_space_map(isolation_ctmc.state_space, middle_ctmc.state_space, p, q)
        self.upto_ = compute_upto(isolation_ctmc.probability_matrix(middle_break_points[0]) * projection, self.through_)

        self.between_ = compute_between(self.through_)

    def get_state_space(self, i):
        """Return the state space for interval i."""
        if i < self.no_middle_states:
            return self.middle.state_space
        else:
            return self.ancestral.state_space


## Class that can construct HMMs ######################################
class AdmixtureModel(Model):
    """Class wrapping the code that generates an isolation model HMM
        with variable coalescence rates in the different intervals."""

    # Determines which initial state to start the CTMCs in
    INITIAL_11 = 0
    INITIAL_12 = 1
    INITIAL_22 = 2

    def __init__(self, initial_configuration, no_isolation_intervals, no_middle_intervals, no_ancestral_intervals):
        """Construct the model.

        This builds the state spaces for the CTMCs but the matrices for the
        HMM since those will depend on the rate parameters."""
        super(AdmixtureModel, self).__init__()

        assert initial_configuration in (AdmixtureModel.INITIAL_11, AdmixtureModel.INITIAL_12, AdmixtureModel.INITIAL_22)
        self.initial_state = initial_configuration

        self.isolation_state_space = Isolation()
        self.middle_state_space = Admixture()
        self.ancestral_state_space = Single()

        self.no_isolation_states = no_isolation_intervals
        self.no_middle_states = no_middle_intervals
        self.no_ancestral_states = no_ancestral_intervals
        self.no_states = no_isolation_intervals + no_middle_intervals + no_ancestral_intervals

    def get_middle_break_points(self, tau_1, tau_2, coal_21, coal_22):
        # FIXME: this should take into account the coalescence rate in each epoch and use a truncated exponential
        #mean_coal = (coal_21 + coal_22) / 2.0
        return uniform_break_points(self.no_middle_states, tau_1, tau_1 + tau_2)

    def get_ancestral_break_points(self, tau_1, tau_2, coal_a):
        return exp_break_points(self.no_ancestral_states, coal_a, tau_1 + tau_2)

    def emission_points_12(self, *parameters):
        """Time points to emit from."""
        tau_1, tau_2, coal_11, coal_12, coal_21, coal_22, coal_a, _, _, _ = parameters
        middle_points = coalescence_points(self.get_middle_break_points(tau_1, tau_2, coal_21, coal_22),
                                           (coal_21+coal_22)/2.0)
        ancestral_points = coalescence_points(self.get_ancestral_break_points(tau_1, tau_2, coal_a), coal_a)
        return middle_points + ancestral_points

    def emission_points(self, *parameters):
        """Time points to emit from."""
        # FIXME: should depend on initial state
        return self.emission_points_12(*parameters)

    def build_ctmc_system(self, *parameters):
        """Construct CTMCs and compute HMM matrices given the admixture time, split time time,
        and the rates.
        """
        tau_1, tau_2, coal_11, coal_12, coal_21, coal_22, coal_a, recomb, p, q = parameters

        isolation_rates = make_rates_table_isolation(coal_11, coal_12, recomb)
        middle_rates = make_rates_table_admixture(coal_21, coal_22, recomb)
        ancestral_rates = make_rates_table_single(coal_a, recomb)

        isolation_ctmc = make_ctmc(self.isolation_state_space, isolation_rates)
        middle_ctmc = make_ctmc(self.middle_state_space, middle_rates)
        ancestral_ctmc = make_ctmc(self.ancestral_state_space, ancestral_rates)

        middle_break_points = self.get_middle_break_points(tau_1, tau_2, coal_21, coal_22)
        ancestral_break_points = self.get_ancestral_break_points(tau_1, tau_2, coal_a)

        # FIXME: depends on initial configuration option to the model...
        return AdmixtureCTMCSystem12(isolation_ctmc, middle_ctmc, ancestral_ctmc, p=p, q=q,
                                     middle_break_points=middle_break_points,
                                     ancestral_break_points=ancestral_break_points)



model = AdmixtureModel(AdmixtureModel.INITIAL_12, 0, 3, 3)
parameters = (0.0001, 0.0001, 1200.0, 1200.0, 1200.0, 1200.0, 1200.0, 0.4, 0.1, 0.0)
pi, trans_probs, emis_probs = model.build_hidden_markov_model(parameters)

print pi.getHeight(), pi.getWidth()
print trans_probs.getHeight(), trans_probs.getWidth()

s = 0.0
for i in xrange(pi.getHeight()):
    print 'pi[{}] == {}'.format(i, pi[0,i])
    s += pi[0, i]
print s
print

for i in xrange(trans_probs.getHeight()):
    print 'T[{},]'.format(i),
    s = 0.0
    for j in xrange(trans_probs.getWidth()):
        print trans_probs[i, j],
        s += trans_probs[i, j]
    print
    print s
print
