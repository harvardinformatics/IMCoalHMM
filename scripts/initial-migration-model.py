#!/usr/bin/env python

"""Script for estimating parameters in an initial migration model.
"""

from argparse import ArgumentParser

from IMCoalHMM.likelihood import Likelihood, maximum_likelihood_estimate
#from IMCoalHMM.isolation_with_migration_model import IsolationMigrationModel
from pyZipHMM import Forwarder

from IMCoalHMM.isolation_with_migration_model import IsolationMigrationModel

import isolation_with_migration_model2


def transform(params):
    """
    Translate the parameters to the input and output parameter space.
    """
    if len(params)==6:
        isolation_time, migration_time, coal_rate, recomb_rate, mig_rate, outgroup = params
        return isolation_time, migration_time, 2 / coal_rate, recomb_rate, mig_rate, outgroup
    
    isolation_time, migration_time, coal_rate, recomb_rate, mig_rate = params
    return isolation_time, migration_time, 2 / coal_rate, recomb_rate, mig_rate


def main():
    """
    Run the main script.
    """
    usage = """%(prog)s [options] <forwarder dirs>

This program estimates the parameters of an isolation model with an initial migration period with two species
and uniform coalescence and recombination rates."""

    parser = ArgumentParser(usage=usage, version="%(prog)s 1.2")

    parser.add_argument("--header",
                        action="store_true",
                        default=False,
                        help="Include a header on the output")
    parser.add_argument("-o", "--outfile",
                        type=str,
                        default="/dev/stdout",
                        help="Output file for the estimate (/dev/stdout)")

    parser.add_argument("--logfile",
                        type=str,
                        default=None,
                        help="Log for all points estimated in the optimization")

    parser.add_argument("--ancestral-states",
                        type=int,
                        default=10,
                        help="Number of intervals used to discretize the time in the ancestral population (10)")
    parser.add_argument("--migration-states",
                        type=int,
                        default=10,
                        help="Number of intervals used to discretize the time in the migration period (10)")

    parser.add_argument("--optimizer",
                        type=str,
                        default="Nelder-Mead",
                        help="Optimization algorithm to use for maximizing the likelihood (Nealder-Mead)",
                        choices=['Nelder-Mead', 'Powell', 'L-BFGS-B', 'TNC'])
    
    parser.add_argument("--verbose",
                        default=False,
                        action='store_true')      
    
    parser.add_argument("--emissionComplicated", default=False, action="store_true", help="This will use an emission matrix which is not an approximation.")
    parser.add_argument('--outgroup', action='store_true', default=False, help="This indicates that the alignemnts are not pairwise but threewise and that the last entry will be ")
    
    parser.add_argument('--constant_break_points', default=False, action="store_true", help='If enabled, the break points will be fixed throughout the analysis but the epochs will change')
    parser.add_argument('--breakpoints_tail_pieces', default=0, type=int, help='this produce a tail of last a number of pieces on the breakpoints')
    parser.add_argument('--breakpoints_time', default=1.0, type=float, help='this number moves the breakpoints up and down. Smaller values will give sooner timeperiods.')


    optimized_params = [
        ('isolation-period', 'time where the populations have been isolated', 1e6 / 1e9),
        ('migration-period', 'time period where the populations exchanged genes', 1e6 / 1e9),
        ('theta', 'effective population size in 4Ne substitutions', 1e6 / 1e9),
        ('rho', 'recombination rate in substitutions', 0.4),
        ('migration-rate', 'migration rate in number of migrations per substitution', 200.0)
    ]

    for parameter_name, description, default in optimized_params:
        parser.add_argument("--%s" % parameter_name,
                            type=float,
                            default=default,
                            help="Initial guess at the %s (%g)" % (description, default))

    parser.add_argument('alignments', nargs='+', help='Alignments in ZipHMM format')

    options = parser.parse_args()
    if len(options.alignments) < 1:
        parser.error("Input alignment not provided!")
    if options.outgroup and not options.emissionComplicated :
        parser.error("You can't have an outgroup without the complicated emission probabilities!")
        
    # get options
    no_migration_states = options.migration_states
    no_ancestral_states = options.ancestral_states
    theta = options.theta
    rho = options.rho

    forwarders = [Forwarder.fromDirectory(arg) for arg in options.alignments]

    init_isolation_time = options.isolation_period
    init_migration_time = options.migration_period
    init_coal = 1 / (theta / 2)
    init_recomb = rho
    init_migration = options.migration_rate
    if options.outgroup:
        init_outgroup = (init_isolation_time+init_migration_time)*3

    if options.emissionComplicated:
        if options.outgroup:
            base_log_likelihood = Likelihood(isolation_with_migration_model2.IsolationMigrationModel(no_migration_states, no_ancestral_states, outgroup=True), forwarders)
        elif options.constant_break_points:
            base_log_likelihood = Likelihood(isolation_with_migration_model2.IsolationMigrationModelConstantBreaks(no_migration_states+ no_ancestral_states, 
                                                                                                                   breaktail=options.breakpoints_tail_pieces,
                                                                                                                   breaktimes=options.breakpoints_time), forwarders)
        else:
            base_log_likelihood = Likelihood(isolation_with_migration_model2.IsolationMigrationModel(no_migration_states, no_ancestral_states), forwarders)
    else:
        base_log_likelihood = Likelihood(IsolationMigrationModel(no_migration_states, no_ancestral_states), forwarders)
    initial_parameters = (init_isolation_time, init_migration_time, init_coal, init_recomb, init_migration)
    if options.outgroup:
        initial_parameters = (init_isolation_time, init_migration_time, init_coal, init_recomb, init_migration, init_outgroup)
    
    if options.verbose:
        def log_likelihood(params):
            val=base_log_likelihood(params)
            print str(params)+"="+str(val)
            return val
    else:
        log_likelihood=base_log_likelihood
    
    
    if options.logfile:
        with open(options.logfile, 'w') as logfile:

            if options.header:
                print >> logfile, '\t'.join(['isolation.period', 'migration.period',
                                             'theta', 'rho', 'migration'])

            mle_parameters = \
                maximum_likelihood_estimate(log_likelihood, initial_parameters,
                                            log_file=logfile, optimizer_method=options.optimizer,
                                            log_param_transform=transform)
    else:
        mle_parameters = \
            maximum_likelihood_estimate(log_likelihood, initial_parameters,
                                        optimizer_method=options.optimizer)

    max_log_likelihood = log_likelihood(mle_parameters)
    with open(options.outfile, 'w') as outfile:
        if options.header:
            print >> outfile, '\t'.join(['isolation.period', 'migration.period',
                                         'theta', 'rho', 'migration', 'log.likelihood'])
        print >> outfile, '\t'.join(map(str, transform(mle_parameters) + (max_log_likelihood,)))


if __name__ == '__main__':
    main()
