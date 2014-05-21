#!/usr/bin/env python

"""Script for estimating parameters in an initial migration model.
"""

from argparse import ArgumentParser

from IMCoalHMM.likelihood import Likelihood
from IMCoalHMM.isolation_with_migration_model import IsolationMigrationModel
from pyZipHMM import Forwarder


from IMCoalHMM.mcmc import MCMC, LogNormPrior, ExpLogNormPrior
from math import log


def transform(params):
    """
    Translate the parameters to the input and output parameter space.
    """
    isolation_time, migration_time, coal_rate, recomb_rate, mig_rate = params
    return isolation_time, migration_time, 2 / coal_rate, recomb_rate, mig_rate


def main():
    """
    Run the main script.
    """
    usage = """%(prog)s [options] <forwarder dirs>

This program estimates the parameters of an isolation model with an initial migration period with two species
and uniform coalescence and recombination rates."""

    parser = ArgumentParser(usage=usage, version="%(prog)s 1.1")

    parser.add_argument("-o", "--outfile",
                        type=str,
                        default="/dev/stdout",
                        help="Output file for the estimate (/dev/stdout)")

    parser.add_argument("--ancestral-states",
                        type=int,
                        default=10,
                        help="Number of intervals used to discretize the time in the ancestral population (10)")
    parser.add_argument("--migration-states",
                        type=int,
                        default=10,
                        help="Number of intervals used to discretize the time in the migration period (10)")

    parser.add_argument("-n", "--samples",
                        type=int,
                        default=500,
                        help="Number of samples to draw (500)")

    parser.add_argument("-k", "--thinning",
                        type=int,
                        default=100,
                        help="Number of MCMC steps between samples (100)")

    meta_params = [
        ('isolation-period', 'time where the populations have been isolated', 1e6 / 1e9),
        ('migration-period', 'time period where the populations exchanged genes', 1e6 / 1e9),
        ('theta', 'effective population size in 4Ne substitutions', 1e6 / 1e9),
        ('rho', 'recombination rate in substitutions', 0.4),
        ('migration-rate', 'migration rate in number of migrations per substitution', 200.0)
    ]

    for parameter_name, description, default in meta_params:
        parser.add_argument("--%s" % parameter_name,
                            type=float,
                            default=default,
                            help="Meta-parameter mean of the %s (%g)" % (description, default))

    parser.add_argument('alignments', nargs='+', help='Alignments in ZipHMM format')

    options = parser.parse_args()
    if len(options.alignments) < 1:
        parser.error("Input alignment not provided!")

    # Specify priors and proposal distributions... 
    # I am sampling in log-space to make it easier to make a random walk
    isolation_period_prior = LogNormPrior(log(options.isolation_period))
    migration_period_prior = LogNormPrior(log(options.migration_period))
    coal_prior = LogNormPrior(log(1/(options.theta/2)))
    rho_prior = LogNormPrior(log(options.rho))
    migration_rate_prior = ExpLogNormPrior(options.migration_rate)
    priors = [isolation_period_prior, migration_period_prior,
              coal_prior, rho_prior, migration_rate_prior]

    # Draw initial parameters from the priors
    init_params = [pi.sample() for pi in priors]

    # Read data and provide likelihood function
    forwarders = [Forwarder.fromDirectory(arg) for arg in options.alignments]
    log_likelihood = Likelihood(IsolationMigrationModel(options.migration_states,
                                                        options.ancestral_states),
                                forwarders)

    mcmc = MCMC(priors, log_likelihood)

    with open(options.outfile, 'w') as outfile:
        print >> outfile, '\t'.join(['isolation.period', 'migration.period',
                                     'theta', 'rho', 'migration', 'posterior'])
        
        for _ in xrange(options.samples):
            params, post = mcmc.sample(thinning=options.thinning)
            print >> outfile, '\t'.join(map(str, transform(params) + (post,)))
            outfile.flush()

if __name__ == '__main__':
    main()