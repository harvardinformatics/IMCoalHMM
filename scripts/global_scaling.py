'''
Created on Oct 22, 2014

@author: svendvn
'''

from math import log, exp,sqrt

class Global_scaling(object):
    '''
    classdocs
    '''


    def __init__(self,theta=1.0, params=[0.5,10], alphaDesired=0.234):
        '''
        Constructor. theta is the factor that is multiplied on all proposals. It is updated throughout so input to the constructor is only a 
        starting value. 
        alpha is the power in the updating rule theta_{count+1}=max(0.0001,theta_{count}+1/count^alpha*(1_{accept}(true)*2-1))
        '''
        self.theta=theta
        self.count=1
        self.alpha=params[0]
        self.multip=params[1]
        self.alphaDesired=alphaDesired
        
        
    
    def first_transform(self, params):
        '''
        this takes a vector and transforms it into the scaled space
        '''
        return [exp(log(x)/sqrt(self.theta)) for x in params]
    
     
    def after_transform(self, params):   
        '''
        this takes a vector from scaled space and transforms it back
        '''
        return [exp(log(x)*sqrt(self.theta)) for x in params]
    
    def setTheta(self, new_theta):
        self.theta=new_theta
        
    def update_alpha(self, accept,alphaXY):
        '''
        This updates alpha based on whether or not 'accept' is true or false. 
        We want: accept=True <=> the proposal based on alpha was accepted. 
        
        Other algorithms return two values, that's why we ignore one input. 
        '''
        #0.234 has some special meaning in mcmc acceptance probabilities.
        gamma=self.multip/self.count**self.alpha
        self.theta *= exp(gamma*(alphaXY-self.alphaDesired))
        self.count+=1
        return self.theta
        
        