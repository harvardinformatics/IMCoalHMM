"""
Implementation of basic Particle Swarm Optimisation.
"""

import datetime
import math
import random


class Solution(object):
    """
    Encapsulation of a vector of positions and their corresponding fitness.
    """

    def __init__(self):
        """
        Initialise a new instance of the class.
        :return: A new instance of the class.
        """
        self.positions = []
        self.fitness = 0.0

    def __str__(self):
        """
        Return a string representation of this instance.
        :return: A string representation of this instance.
        """
        token = ' '.join(map(str, self.positions))
        return 'fitness:{0} positions:[{1}]'.format(self.fitness, token)


class Particle(object):
    """
    Implementation of one particle in a swarm.
    """

    def __init__(self):
        """
        Initialise a new instance of the class.
        :return: A new instance of the class.
        """
        self.best = Solution()
        self.current = Solution()
        self.velocities = []


class ExitCondition(object):
    """
    A class providing descriptions for the reason a Particle Swarm Optimisation terminates.
    """

    ABORT = 'ABORT'
    ITERATIONS = 'ITERATIONS'
    TIMEOUT = 'TIMEOUT'


class Context(object):
    """
    Context information for the Particle Swarm optimiser; this instance is passed to the optional log method and
    eventually returned as a result of the optimisation.
    """

    def __init__(self, optimiser):
        """
        Initialise a new instance of the class for the specified optimiser.
        :param optimiser: The optimiser for this instance.
        :return: A new instance of the class.
        """
        assert isinstance(optimiser, Optimiser) or isinstance(optimiser, OptimiserParallel) or isinstance(optimiser , OptimiserParallelRecord)

        self.aborted = False
        self.best = Solution()
        self.elapsed = datetime.timedelta(seconds=0)
        self.exit_condition = None
        self.iteration = 0
        self.optimiser = optimiser
        self.particles = []
        self.start = datetime.datetime.now()

class Optimiser(object):
    """
    A Particle Swarm Optimiser.
    """

    def __init__(self):
        """
        Initialise a new instance of the class, setting the maximum number of iterations to 500, no maximum execution
        time, the particle count to 100, the phi_particle to 0.3, the phi_swarm to 0.1, the omega to 0.9, and the
        maximum initial velocity to 0.02.
        :return: A new instance of the class.
        """
        self.omega = 0.95
        self.phi_particle = 0.6
        self.phi_swarm = 0.8
        self.log = None
        self.max_iterations = 500
        self.max_initial_velocity = 0.002
        self.particle_count = 100
        self.timeout = None

    def maximise(self, fitness_function, parameter_count):
        """
        Attempt to find a maximum set of values for a specified fitness function; the number of dimensions in the
        problem domain is represented by the specified parameter count.
        :param fitness_function: The fitness function to maximise.
        :param parameter_count: the number of dimensions in the problem domain.
        :return: An instance of type Context that encapsulates the final state of the algorithm.
        """
        assert hasattr(fitness_function, '__call__')
        assert parameter_count > 0

        def fitness_function_wrapper(parameters):
            fitness = fitness_function(parameters)
            if math.isnan(fitness):
                fitness = float('-inf')
            return fitness

        context = Context(self)

        # Create the initial particles.
        for _ in xrange(self.particle_count):
            particle = Particle()
            context.particles.append(particle)

            # Initialise the particle's position with a uniformly distributed random vector.
            particle.current.positions = [random.uniform(0.0, 1.0) for _ in xrange(parameter_count)]
            particle.current.fitness = fitness_function_wrapper(tuple(particle.current.positions))

            # Initialise the particle's best known position to its initial position.
            particle.best.positions = tuple(particle.current.positions)
            particle.best.fitness = particle.current.fitness

            # Initialise the particle's velocity.
            initialise_velocity = lambda: random.uniform(
                -self.max_initial_velocity,
                +self.max_initial_velocity)
            particle.velocities = [initialise_velocity() for _ in xrange(parameter_count)]

        # Initially assign the best solution for the swarm.
        context.best.fitness = context.particles[0].best.fitness
        context.best.positions = context.particles[0].best.positions
        for particle in context.particles[1:]:
            if context.best.fitness is None or particle.best.fitness > context.best.fitness:
                context.best.fitness = particle.best.fitness
                context.best.positions = particle.best.positions

        # Loop until an exit condition occurs.
        while True:

            # Log the iteration before it's lost forever.
            context.elapsed = datetime.datetime.now() - context.start
            context.iteration += 1
            self.__log(context)

            # Check for exit conditions.
            if context.aborted:
                context.exit_condition = ExitCondition.ABORT
                return context
            if self.max_iterations is not None and context.iteration >= self.max_iterations:
                context.exit_condition = ExitCondition.ITERATIONS
                return context
            if self.timeout is not None and context.elapsed > self.timeout:
                context.exit_condition = ExitCondition.TIMEOUT
                return context

            # Loop over all particles in the swarm.
            for particle in context.particles:

                # Pick two random numbers that will be applied to each velocity.
                r_particle = random.uniform(0.0, 1.0)
                r_swarm = random.uniform(0.0, 1.0)

                # Loop over all positions and velocities.
                for i in xrange(parameter_count):
                    velocity = particle.velocities[i]
                    position = particle.current.positions[i]
                    best_particle_position = particle.best.positions[i]
                    best_swarm_position = context.best.positions[i]

                    # Update the particle's velocity.
                    new_velocity = 0.0
                    new_velocity += self.omega * velocity
                    new_velocity += self.phi_particle * r_particle * (best_particle_position - position)
                    new_velocity += self.phi_swarm * r_swarm * (best_swarm_position - position)
                    particle.velocities[i] = new_velocity

                    # Update the particle's position
                    particle.current.positions[i] += new_velocity

                # Compute a new fitness for the particle.
                particle.current.fitness = fitness_function_wrapper(tuple(particle.current.positions))

                # Update the particle's best-known position.
                if particle.current.fitness > particle.best.fitness:
                    particle.best.fitness = particle.current.fitness
                    particle.best.positions = tuple(particle.current.positions)

                    # Update the swarm's best-known position.
                    if particle.best.fitness > context.best.fitness:
                        context.best.fitness = particle.best.fitness
                        context.best.positions = particle.best.positions

    def __log(self, context):
        if self.log is not None:
            self.log(context)
    

class OptimiserParallel(object):
    """
    A Particle Swarm Optimiser.
    """

    def __init__(self, starting_areas=None):
        """
        Initialise a new instance of the class, setting the maximum number of iterations to 500, no maximum execution
        time, the particle count to 100, the phi_particle to 0.3, the phi_swarm to 0.1, the omega to 0.9, and the
        maximum initial velocity to 0.02.
        :return: A new instance of the class.
        """
        self.omega = 0.95
        self.phi_particle = 0.55
        self.phi_swarm = 0.55
        self.log = None
        self.max_iterations = 400
        self.max_initial_velocity = 0.002
        self.particle_count = 100
        self.timeout = None
        self.starting_area_jitter=0.01
        self.starting_areas = starting_areas
        print "starting area", self.starting_areas
        
        

    def maximise(self, fitness_function, parameter_count,processes):
        """
        Attempt to find a maximum set of values for a specified fitness function; the number of dimensions in the
        problem domain is represented by the specified parameter count.
        :param fitness_function: The fitness function to maximise.
        :param parameter_count: the number of dimensions in the problem domain.
        :return: An instance of type Context that encapsulates the final state of the algorithm.
        """
        
        
        
        assert hasattr(fitness_function, '__call__')
        assert parameter_count > 0

        
        import multiprocessing
        pool = multiprocessing.Pool(processes=processes)
        

        context = Context(self)

        # Create the initial particles.
        listOfArgs=[]
        if self.starting_areas is not None:
            no_areas=len(self.starting_areas)
            particles_of_each=self.particle_count/no_areas                      #integer division intended
            looper=[particles_of_each]*no_areas
            for i in xrange(self.particle_count-particles_of_each*no_areas):    #keep number of particles fixed.
                looper[i]+=1
            for i,up_to in enumerate(looper):
                for a in xrange(up_to-1):
                    particle = Particle()
                    context.particles.append(particle)
                    particle.current.positions=[self.starting_areas[i][j]+
                                              (self.starting_area_jitter*random.uniform(0.0, 1.0)
                                               -self.starting_area_jitter/2) for j in xrange(parameter_count)]    
                    listOfArgs.append(particle.current.positions)
                    
                #adding the starting area centrum also.
                listOfArgs.append(self.starting_areas[i])
        else:
            for _ in xrange(self.particle_count):
                particle = Particle()
                context.particles.append(particle)

                particle.current.positions = [random.uniform(0.0, 1.0) for _ in xrange(parameter_count)]
                
                listOfArgs.append(particle.current.positions)
        
        listOfResults=pool.map(fitness_function, listOfArgs)
        
#         for n,particle in enumerate(context.particles):
#             chains[n].remote_start(particle.current.positions)
#         for n,particle in enumerate(context.particles):
#             chains[n].remote_complete()
#             particle.current.fitness=chains[n].val
        
        for n,particle in enumerate(context.particles):
            particle.current.fitness=listOfResults[n]
            # Initialise the particle's best known position to its initial position.
            particle.best.positions = tuple(particle.current.positions)
            particle.best.fitness = particle.current.fitness

            # Initialise the particle's velocity.
            initialise_velocity = lambda: random.uniform(
                -self.max_initial_velocity,
                +self.max_initial_velocity)
            particle.velocities = [initialise_velocity() for _ in xrange(parameter_count)]

        # Initially assign the best solution for the swarm.
        context.best.fitness = context.particles[0].best.fitness
        context.best.positions = context.particles[0].best.positions
        for particle in context.particles[1:]:
            if context.best.fitness is None or particle.best.fitness > context.best.fitness:
                context.best.fitness = particle.best.fitness
                context.best.positions = particle.best.positions

        # Loop until an exit condition occurs.
        while True:

            # Log the iteration before it's lost forever.
            context.elapsed = datetime.datetime.now() - context.start
            context.iteration += 1
            self.__log(context)

            # Check for exit conditions.
            if context.aborted:
                context.exit_condition = ExitCondition.ABORT
                return context
            if self.max_iterations is not None and context.iteration >= self.max_iterations:
                context.exit_condition = ExitCondition.ITERATIONS
                return context
            if self.timeout is not None and context.elapsed > self.timeout:
                context.exit_condition = ExitCondition.TIMEOUT
                return context

            # Loop over all particles in the swarm.
            listOfArgs=[]
            for particle in context.particles:

                # Pick two random numbers that will be applied to each velocity.
                r_particle = random.uniform(0.0, 1.0)
                r_swarm = random.uniform(0.0, 1.0)

                # Loop over all positions and velocities.
                for i in xrange(parameter_count):
                    velocity = particle.velocities[i]
                    position = particle.current.positions[i]
                    best_particle_position = particle.best.positions[i]
                    best_swarm_position = context.best.positions[i]

                    # Update the particle's velocity.
                    new_velocity = 0.0
                    new_velocity += self.omega * velocity
                    new_velocity += self.phi_particle * r_particle * (best_particle_position - position)
                    new_velocity += self.phi_swarm * r_swarm * (best_swarm_position - position)
                    particle.velocities[i] = new_velocity

                    # Update the particle's position
                    particle.current.positions[i] += new_velocity
                listOfArgs.append(particle.current.positions)
            try:
                listOfResults=pool.map(fitness_function, listOfArgs) 
            except OverflowError:
                for i in listOfArgs:
                    try:
                        fitness_function(i)
                    except:
                        raise ValueError("these parameters gave overflow:"+ str(i))
            
            for n,particle in enumerate(context.particles):
                particle.current.fitness=listOfResults[n]
                # Update the particle's best-known position.
                if particle.current.fitness > particle.best.fitness:
                    particle.best.fitness = particle.current.fitness
                    particle.best.positions = tuple(particle.current.positions)

                    # Update the swarm's best-known position.
                    if particle.best.fitness > context.best.fitness:
                        context.best.fitness = particle.best.fitness
                        context.best.positions = particle.best.positions
        pool.close()

    def __log(self, context):
        if self.log is not None:
            self.log(context)
            
            
class OptimiserParallelRecord(object):
    """
    A Particle Swarm Optimiser.
    """

    def __init__(self, starting_areas=None):
        """
        Initialise a new instance of the class, setting the maximum number of iterations to 500, no maximum execution
        time, the particle count to 100, the phi_particle to 0.3, the phi_swarm to 0.1, the omega to 0.9, and the
        maximum initial velocity to 0.02.
        :return: A new instance of the class.
        """
        self.omega = 0.8
        self.phi_particle = 0.55
        self.phi_swarm = 0.55
        self.log = None
        self.max_iterations = 500
        self.max_initial_velocity = 0.002
        self.particle_count = 100
        self.timeout = None
        self.starting_area_jitter=0.01
        self.starting_areas = starting_areas
        
        print "starting area", self.starting_areas
        
        

    def maximise(self, fitness_function, parameter_count,processes):
        """
        Attempt to find a maximum set of values for a specified fitness function; the number of dimensions in the
        problem domain is represented by the specified parameter count.
        :param fitness_function: The fitness function to maximise.
        :param parameter_count: the number of dimensions in the problem domain.
        :return: An instance of type Context that encapsulates the final state of the algorithm.
        """
        self.results=[]
        
        
        assert hasattr(fitness_function, '__call__')
        assert parameter_count > 0

        
        import multiprocessing
        pool = multiprocessing.Pool(processes=processes)
        

        context = Context(self)

        # Create the initial particles.
        listOfArgs=[]
        if self.starting_areas is not None:
            no_areas=len(self.starting_areas)
            particles_of_each=self.particle_count/no_areas                      #integer division intended
            looper=[particles_of_each]*no_areas
            for i in xrange(self.particle_count-particles_of_each*no_areas):    #keep number of particles fixed.
                looper[i]+=1
            for i,up_to in enumerate(looper):
                for _ in xrange(up_to):
                    particle = Particle()
                    context.particles.append(particle)
                    particle.current.positions=[self.starting_areas[i][j]+
                                              (self.starting_area_jitter*random.uniform(0.0, 1.0)
                                               -self.starting_area_jitter/2) for j in xrange(parameter_count)]    
                    listOfArgs.append(particle.current.positions)
        else:
            for _ in xrange(self.particle_count):
                particle = Particle()
                context.particles.append(particle)

                particle.current.positions = [random.uniform(0.0, 1.0) for _ in xrange(parameter_count)]
                
                listOfArgs.append(particle.current.positions)
        
        self.results.append([j for i in listOfArgs for j in i])

        listOfResults=pool.map(fitness_function, listOfArgs)
        
#         for n,particle in enumerate(context.particles):
#             chains[n].remote_start(particle.current.positions)
#         for n,particle in enumerate(context.particles):
#             chains[n].remote_complete()
#             particle.current.fitness=chains[n].val
        
        for n,particle in enumerate(context.particles):
            particle.current.fitness=listOfResults[n]
            # Initialise the particle's best known position to its initial position.
            particle.best.positions = tuple(particle.current.positions)
            particle.best.fitness = particle.current.fitness

            # Initialise the particle's velocity.
            initialise_velocity = lambda: random.uniform(
                -self.max_initial_velocity,
                +self.max_initial_velocity)
            particle.velocities = [initialise_velocity() for _ in xrange(parameter_count)]

        # Initially assign the best solution for the swarm.
        context.best.fitness = context.particles[0].best.fitness
        context.best.positions = context.particles[0].best.positions
        for particle in context.particles[1:]:
            if context.best.fitness is None or particle.best.fitness > context.best.fitness:
                context.best.fitness = particle.best.fitness
                context.best.positions = particle.best.positions

        # Loop until an exit condition occurs.
        while True:

            # Log the iteration before it's lost forever.
            context.elapsed = datetime.datetime.now() - context.start
            context.iteration += 1
            self.__log(context)

            # Check for exit conditions.
            if context.aborted:
                context.exit_condition = ExitCondition.ABORT
                return context, self.results
            if self.max_iterations is not None and context.iteration >= self.max_iterations:
                context.exit_condition = ExitCondition.ITERATIONS
                return context, self.results
            if self.timeout is not None and context.elapsed > self.timeout:
                context.exit_condition = ExitCondition.TIMEOUT
                return context, self.results

            # Loop over all particles in the swarm.
            listOfArgs=[]
            for particle in context.particles:

                # Pick two random numbers that will be applied to each velocity.
                r_particle = random.uniform(0.0, 1.0)
                r_swarm = random.uniform(0.0, 1.0)

                # Loop over all positions and velocities.
                for i in xrange(parameter_count):
                    velocity = particle.velocities[i]
                    position = particle.current.positions[i]
                    best_particle_position = particle.best.positions[i]
                    best_swarm_position = context.best.positions[i]

                    # Update the particle's velocity.
                    new_velocity = 0.0
                    new_velocity += self.omega * velocity
                    new_velocity += self.phi_particle * r_particle * (best_particle_position - position)
                    new_velocity += self.phi_swarm * r_swarm * (best_swarm_position - position)
                    particle.velocities[i] = new_velocity

                    # Update the particle's position
                    particle.current.positions[i] += new_velocity
                listOfArgs.append(particle.current.positions)
            self.results.append([j for i in listOfArgs for j in i])
            try:
                listOfResults=pool.map(fitness_function, listOfArgs) 
            except OverflowError:
                for i in listOfArgs:
                    try:
                        fitness_function(i)
                    except:
                        raise ValueError("these parameters gave overflow:"+ str(i))
            
            for n,particle in enumerate(context.particles):
                particle.current.fitness=listOfResults[n]
                # Update the particle's best-known position.
                if particle.current.fitness > particle.best.fitness:
                    particle.best.fitness = particle.current.fitness
                    particle.best.positions = tuple(particle.current.positions)

                    # Update the swarm's best-known position.
                    if particle.best.fitness > context.best.fitness:
                        context.best.fitness = particle.best.fitness
                        context.best.positions = particle.best.positions
        pool.close()

    def __log(self, context):
        if self.log is not None:
            self.log(context)


if __name__=='__main__':
    def f(x):
        return -(x[0]-0.5)**2-(x[1]-0.5)**2
    opr= OptimiserParallelRecord()
    r,t= opr.maximise(f, 2, 1)
    import numpy
    a = numpy.asarray(t)
    numpy.savetxt("/home/svendvn/Dropbox/Bioinformatik/her.csv", a, delimiter=",")