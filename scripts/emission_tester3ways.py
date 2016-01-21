"""
Code for generating trees using ms and comparing them to the emission matrix of the variable_migration_model2.
"""

#!/usr/bin/env python

import newick.tree, newick
import pylab
import re
import subprocess
from argparse import ArgumentParser
import bisect
from bisect import bisect
from break_points2 import uniform_break_points, exp_break_points
from numpy import array, zeros, ndarray
from numpy import sum as npsum

parser = ArgumentParser(usage="generate from ms-variable-migration-model and construct emission matrices", version="%(prog)s 1.0")

parser.add_argument("-p","--prefix",
                    type=str,
                    default="/home/svendvn/",
                    help="All files generated by the script have programmer-defined names but they should be saved somewhere. That directory is supplied here")
parser.add_argument("-y","--python_prefix",
                    type=str,
                    default="/home/svendvn/git/IMCoalHMM/scripts/",
                    help="If the python scripts is not placed in the same folder as here prefix it should be pointed out here with their directory")

parser.add_argument('-r',"--reps", type=int, default=1, help="number of times 1000000 positions should be simulated.")
parser.add_argument('-m',"--m", type=int, default=1, help="scheme to use")
#TABLE:
    #m=1: ILS model, initial_distribution
    #m=2: initial_migration med og uden outgroup, emissionssandsynligheder


options=parser.parse_args()
fileprefix=options.prefix
if options.python_prefix:
    pythonprefix=options.python_prefix
else:
    pythonprefix=options.prefix


_MS_PATH = 'ms'
_SEQGEN_PATH= 'seq-gen'
coal_rho = 800.0
seg_length = 1000000
s2=seg_length/10.0
Ne=20000
gen=25
mu=1e-9
rho_per_gen=1e-8
new_val=1.0

theta_years=4*Ne*gen
#coal_rho=rho_per_gen*4*Ne*gen
theta_subs=mu*theta_years
rho_subs=rho_per_gen/(mu*gen)

substime_first_change=0.0005
substime_second_change=0.002
substime_third_change=0.0070
time_first_change=substime_first_change/theta_subs
time_second_change=substime_second_change/theta_subs
time_third_change=substime_third_change/theta_subs
reps=options.reps


#ms 4 1 -T -r ${coal_rho} ${seg_length} -I 2 2 2 -em ${mstime_for_change} 1 2 $changed_migration -em ${mstime_for_change} 2 1 $changed_migration2 -ej $mstime_for_change_back 1 2
def simulate_forest(forest_file,sequence_file,align_dir_file):
    seqgen_args= ['-q','-mHKY','-l', str(seg_length),'-s',str(theta_subs),'-p',str(s2),forest_file]
#     ms_args = ['4', '1', '-T', '-r', str(1000.0), str(seg_length), '-I', '2', '2', '2', '1.0','-em',str(time_first_change),'1','2',str(new_val), 
#                '-em', str(time_second_change),'1','2',str(old_val),'-em',str(time_second_change), '2','1', str(new_val2), '-em', str(time_third_change), '2','1', str(old_val)]
    ms_args = ['3', '1', '-T', '-r', str(coal_rho), str(seg_length), '-I', '3', '1', '1','1','0.0', '-ej',str(time_first_change),'1','2',
               '-ej',str(time_second_change),'2','3']
        #python /home/svendvn/workspace/IMCoalHMM/scripts/prepare-alignments.py --names=1,2 ${seqfile} phylip ${ziphmmfile11} --where_path_ends 3

    with open(forest_file, 'w') as f:
        p = subprocess.Popen([_MS_PATH] + ms_args, stdout=subprocess.PIPE)
        line_number = 0
        for line in p.stdout.readlines():
            line_number += 1
            if line_number >= 4 and '//' not in line:
                f.write(line)
    print "."

    with open(sequence_file, 'w') as f:
        p = subprocess.Popen([_SEQGEN_PATH] + seqgen_args, stdout=subprocess.PIPE)
        print ","
        line_number = 0
        for line in p.stdout.readlines():
            line_number += 1
            if line_number >= 1:
                f.write(line)
    print ","
    subprocess.call(['python',pythonprefix+'prepare-alignments.py', '--names=1,2,3', sequence_file,'phylip', align_dir_file, '--where_path_ends', str(3)])


def simulate_forest2(forest_file,sequence_file,align_dir_file): 
    '''
    iim with and without outgroup
    '''
    
    seqgen_args= ['-q','-mHKY','-l', str(seg_length),'-s',str(theta_subs),'-p',str(s2),forest_file]
#     ms_args = ['4', '1', '-T', '-r', str(1000.0), str(seg_length), '-I', '2', '2', '2', '1.0','-em',str(time_first_change),'1','2',str(new_val), 
#                '-em', str(time_second_change),'1','2',str(old_val),'-em',str(time_second_change), '2','1', str(new_val2), '-em', str(time_third_change), '2','1', str(old_val)]
    ms_args = ['3', '1', '-T', '-r', str(1000.0), str(seg_length), '-I', '3', '1', '1','1','0.0', '-em',str(time_first_change),'1','2',str(new_val),
               '-em',str(time_first_change),'2','1',str(new_val),'-ej', str(time_second_change),'1','2','-ej', str(time_third_change),'2','3']
    #em {mstime_for_change} 2 1 {changed_migration} -em {mstime_for_change} 1 2 {changed_migration} -ej {mstime_for_change2} 2 1 -ej {mstime_for_outgroup} 1 3
        #python /home/svendvn/workspace/IMCoalHMM/scripts/prepare-alignments.py --names=1,2 ${seqfile} phylip ${ziphmmfile11} --where_path_ends 3

    with open(forest_file, 'w') as f:
        p = subprocess.Popen([_MS_PATH] + ms_args, stdout=subprocess.PIPE)
        line_number = 0
        for line in p.stdout.readlines():
            line_number += 1
            if line_number >= 4 and '//' not in line:
                f.write(line)
    print "."

    with open(sequence_file, 'w') as f:
        p = subprocess.Popen([_SEQGEN_PATH] + seqgen_args, stdout=subprocess.PIPE)
        print ","
        line_number = 0
        for line in p.stdout.readlines():
            line_number += 1
            if line_number >= 1:
                f.write(line)
    print ","
    subprocess.call(['python',pythonprefix+'prepare-alignments.py', '--names=1,2', sequence_file,'phylip', align_dir_file[0], '--where_path_ends', str(3)])
    subprocess.call(['python',pythonprefix+'prepare-alignments.py', '--names=1,2,3', sequence_file,'phylip', align_dir_file[1], '--where_path_ends', str(3)])

coal_rate=1000
rho=0.4
mig_rate=new_val/theta_subs

if options.m==2:
    break_points_12 = uniform_break_points(10,substime_first_change,substime_second_change)
    break_points_123 = exp_break_points(10, 1000.0, substime_second_change) #here we implicitly assume coal_last=coal_123=coal123=1000.0
else:
    break_points_12 = uniform_break_points(3,substime_first_change,substime_second_change)
    break_points_123 = exp_break_points(3, 1000.0, substime_second_change) #here we implicitly assume coal_last=coal_123=coal123=1000.0

bre=break_points_12.tolist()+break_points_123.tolist()
print "ms_bottom_time",time_first_change
print bre
print break_points_12
print break_points_123
bre_ms=[b/theta_subs for b in bre]
print bre_ms

def getCategories(T12,T13,T23):
    return bisect(bre_ms,T12)-1, bisect(bre_ms,T13)-1, bisect(bre_ms,T23)-1

class PairTMRCA(newick.tree.TreeVisitor):
    '''class for finding the TMRCA for all the pairs of leaves in a tree'''
        
    def pre_visit_edge(self, src, bootstrap, length, dst):
        subtree_leaves = set(map(int,dst.get_leaves_identifiers()))
        rest_leaves = self.all_leaves.difference(subtree_leaves)
        # for all leaves that have not been visited already, 
        # such that i is in subtree_leaves and j is in rest_leaves
        # update the corresponding tmrca with length
        for i in subtree_leaves:
            for j in rest_leaves:
                    min_leaf = min(i, j)
                    max_leaf = max(i, j)
                    self.tmrca[(min_leaf, max_leaf)] += length/2

    def get_TMRCA(self, string_tree):
        tree = newick.tree.parse_tree(string_tree)
        self.all_leaves = set(map(int,tree.get_leaves_identifiers()))
        no_leaves = len(self.all_leaves)
        self.tmrca = {}
        # initialize the tmrca to 0
        for i in range(no_leaves-1):
            for j in range(i+1,no_leaves):
                self.tmrca[(i+1,j+1)] = 0
        tree.dfs_traverse(self)
        return self.tmrca

def process_tree(line):
    if line[0] != '[':
        return None, None
    s = line.strip().split("[")[1].split("]")
    return int(s[0]), s[1]

def count_tmrca(filename, subs):
    visitor = PairTMRCA()
    f = open(filename)
    res={}
    tmrca12=[]
    for line in f:
        count, tree = process_tree(line)
        tmrca = visitor.get_TMRCA(tree)

        t12,t13,t23 = getCategories(tmrca[(1,2)],tmrca[(1,3)],tmrca[(2,3)])
        tmrca12.append(t12)
        if t12==t13==t23:
            state=((frozenset([frozenset([2]), frozenset([3]), frozenset([1])]), t12, frozenset([frozenset([1, 2, 3])])),)
            res[state]=res.get(state,0)+count
        elif t12<t13:
            state=(((frozenset([frozenset([2]), frozenset([3]), frozenset([1])]), t12, frozenset([frozenset([1, 2]), frozenset([3])])), (frozenset([frozenset([1, 2]), frozenset([3])]), t13, frozenset([frozenset([1, 2, 3])]))))
            res[state]=res.get(state,0)+count
        elif t13<t12:
            state=(((frozenset([frozenset([2]), frozenset([3]), frozenset([1])]), t13, frozenset([frozenset([1, 3]), frozenset([2])])), (frozenset([frozenset([1, 3]), frozenset([2])]), t23, frozenset([frozenset([1, 2, 3])]))))
            res[state]=res.get(state,0)+count
        else:
            state=(((frozenset([frozenset([2]), frozenset([3]), frozenset([1])]), t23, frozenset([frozenset([2, 3]), frozenset([1])])), (frozenset([frozenset([2, 3]), frozenset([1])]), t13, frozenset([frozenset([1, 2, 3])]))))
            res[state]=res.get(state,0)+count
    f.close()

    return res, tmrca12

forestfile=fileprefix+"forest.nwk"
alignphyle=fileprefix+"alignemnt.phylip"
align_dirs=[fileprefix+"aligndd2", fileprefix+"aligndd3"]
align_dir=fileprefix+"aligndd"

# class Emissions:
#     
#     def __init__(self, alphabet_size):
#         self.alphabet_size=alphabet_size
#         
#     def getAlphabet_size(self):
#         return self.alphabet_size
#     
#     @abstractmethod
#     def classify(self, nucleotides):
#         pass
#     
# class Emission2(Emissions):
#     
#     def classify(self, nucleotides):
        

def countEmissions(coalTimes,matrix_to_add_to, emissions):
    ans=matrix_to_add_to
    for t,m in zip(coalTimes,emissions):
            ans[t,m]+=1
    return array(ans)

def getEmissions(pathToZiphmm):
    with open(pathToZiphmm+"/original_sequence", 'r') as f:
        seq=f.readline()
    return map(int, seq.split(" "))

rtotal={}
resMat12=zeros(  ( len(bre_ms) , 2 )  )
resMat123=zeros(  ( len(bre_ms) , 64 )  )

for i in xrange(reps):
    if options.m==1:
        subprocess.call(['rm','-R',align_dir])
        simulate_forest(forestfile, alignphyle, align_dir)
    elif options.m==2:
        #subprocess.call(['rm','-Rf',align_dirs[0]])
        #subprocess.call(['rm','-Rf',align_dirs[1]])
        #simulate_forest2(forestfile, alignphyle, align_dirs)
        pass
    print "simulated trees "+str(i)
    r,t12 = count_tmrca(fileprefix+"forest.nwk", theta_subs)
    print "uncovered tree lengths " + str(i)
    for state,count in r.items():
        rtotal[state]=rtotal.get(state,0)+count
    if options.m==2:
        e12=getEmissions(align_dirs[0])
        e123=getEmissions(align_dirs[1])
        resMat12=countEmissions(t12,resMat12,e12)
        resMat123=countEmissions(t12,resMat123,e123)


if options.m==2:
    r12sums=npsum(resMat12,axis=1)
    r123sums=npsum(resMat123,axis=1)
    print r12sums
    print r123sums
    print resMat12
    print resMat123
    
# def constructEmissionProbability(emissvector,filename):
#     with open(filename,'w') as f:
#         for i in xrange(len(emissvector)/2):
#             a=emissvector[i*2]
#             b=emissvector[i*2+1]
#             f.write(str(float(a)/float(a+b+1.0))+" "+str(float(b)/float((a+b+1)))+"\n")
#             
#             
# constructEmissionProbability(ll, fileprefix+"ll_empirical_ms.txt")
# constructEmissionProbability(rr, fileprefix+"rr_empirical_ms.txt")
# constructEmissionProbability(cc, fileprefix+"cc_empirical_ms.txt")

def time_modifier():
    return [(5,substime_first_change),(10,substime_second_change)]

def printPyZipHMM(Matrix):
    finalString=""
    for i in range(Matrix.getHeight()):
        for j in range(Matrix.getWidth()):
            finalString=finalString+" "+str(Matrix[i,j])
        finalString=finalString+"\n"
    return finalString

#this is for testing the already verified variableCoalAndMigrationModel.py
# varb = imp.load_source('variable_migration_model2', pythonprefix+'variable_migration_model2.py')
# def constructTrueEmissionProbability(params, model,filename):
#     cd=varb.VariableCoalAndMigrationRateModel(model, intervals=[5,5,5,5], breaktimes=1.0,breaktail=3, time_modifier=time_modifier)
#     _,_,e,_=cd.build_hidden_markov_model(params)
#     estr=printPyZipHMM(e)
#     with open(filename,'w') as f:
#         f.write(estr)
# parm=[1000,1000,1000,1000,  1000,1000,1000,1000,    500,250,500,500,    500,500,100,500,    0.4]
# constructTrueEmissionProbability(parm,varb.VariableCoalAndMigrationRateModel.INITIAL_11, fileprefix+"ll_theoretical_coalHMM.txt")
# constructTrueEmissionProbability(parm,varb.VariableCoalAndMigrationRateModel.INITIAL_22, fileprefix+"rr_theoretical_coalHMM.txt")
# constructTrueEmissionProbability(parm,varb.VariableCoalAndMigrationRateModel.INITIAL_12, fileprefix+"cc_theoretical_coalHMM.txt")

if options.m==1:
    from IMCoalHMM.ILS import ILSModel
    ad=ILSModel(3,3)
    param1=array([0.009281520636207805, 0.003719596449434415, 845.6317446677223, 845.6317446677223, 845.6317446677223, 845.6317446677223, 1796.544857049849, 0.4])
    param2=array([substime_first_change,substime_second_change, 1000.0,1000.0,1000.0,1000.0,2000.0, 0.4])
    init, _,_=ad.build_hidden_markov_model(param1)
elif options.m==2:
    from isolation_with_migration_model2 import IsolationMigrationModel
    ad12=IsolationMigrationModel(10,10, outgroup=False)
    ad123=IsolationMigrationModel(10,10, outgroup=True)
    param12=array([substime_first_change,substime_second_change, coal_rate,rho, mig_rate])
    param123=array([substime_first_change,substime_second_change, coal_rate,rho, mig_rate,substime_third_change])
    _,_,emiss12=ad12.build_hidden_markov_model(param12)
    _,_,emiss123=ad123.build_hidden_markov_model(param123)
    with open("/home/svendvn/emiss12.txt",'w') as f:
        f.write(printPyZipHMM(emiss12))
    with open("/home/svendvn/emiss123.txt",'w') as f:
        f.write(printPyZipHMM(emiss123))
    with open("/home/svendvn/obs12.txt",'w') as f:
        resMat12.tofile(f)
    with open("/home/svendvn/obs123.txt",'w') as f:
        resMat123.tofile(f)

    
#     estr=printPyZipHMM(e)
#     print estr
#     with open(filename,'w') as f:
#         f.write(estr)

if options.m==1:
    print printPyZipHMM(init)
    print rtotal
    sumOfCounted=0.0
    for state, state_no in ad.tree_map.items():
        print "---------------------"
        print state_no, ": ",state
        print rtotal.get(state,0.0)/float(options.reps*1000000.0), init[1,state_no]
        sumOfCounted+=rtotal.get(state,0.0)/float(options.reps*1000000.0)
    
    print len(ad.tree_map.items())
    
    
    
    print "sumOfCounted", sumOfCounted
elif options.m==2:
    nuc_map = {'A': 0, 'C': 1, 'G': 2, 'T': 3}
    ar=[0]*64
    for i1,v1 in nuc_map.items():
        for i2,v2 in nuc_map.items():
            for i3,v3 in nuc_map.items():
                ar[v1+v2*4+v3*16]="".join(map(str,(i1,i2,i3)))
    print printPyZipHMM(emiss12)
    print printPyZipHMM(emiss123)
    for i in range(len(bre_ms)):
        print "====",i,"12","===="
        As= [emiss12[i,j] for j in range(emiss12.getWidth())]
        Bs= resMat12[i,:]/r12sums[i]
        for a,b in zip(As,Bs):
            print a,b 
        print "====",i,"123","===="
        As= [emiss123[i,j] for j in range(emiss123.getWidth())]
        Bs= resMat123[i,:]/r123sums[i]
        for n,(a,b) in enumerate(zip(As,Bs)):
            print ar[n], a,b 


#parm=[1000,1000,1000,  1000,1000,1000,    0,250,0,    0,100,0,    0.4]
#constructTrueEmissionProbability2(parm,varb.VariableCoalAndMigrationRateAndAncestralModel.INITIAL_11, fileprefix+"ll_theoretical_coalHMM.txt")
#constructTrueEmissionProbability2(parm,varb.VariableCoalAndMigrationRateAndAncestralModel.INITIAL_22, fileprefix+"rr_theoretical_coalHMM.txt")
#constructTrueEmissionProbability2(parm,varb.VariableCoalAndMigrationRateAndAncestralModel.INITIAL_12, fileprefix+"cc_theoretical_coalHMM.txt")


