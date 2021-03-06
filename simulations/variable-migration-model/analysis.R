library(reshape2)
library(ggplot2)
library(scales)

data <- read.table('constant-size-estimates.1Gb.txt', header=FALSE)

no.epochs <- (ncol(data)-2)/4
logL <- data[,ncol(data)]
rec.rage <- data[,ncol(data)-1]

theta1s <- cbind(simulation=factor(1:nrow(data)), data[,1:(no.epochs)])
theta2s <- cbind(simulation=factor(1:nrow(data)), data[,(no.epochs+1):(2*no.epochs)])

qplot(as.numeric(variable), value, color=simulation, geom='line', 
      data=melt(theta1s, id.vars='simulation')) +
  geom_hline(yintercept=0.001, col='red') + 
  scale_y_continuous(trans=log10_trans())#, limits=c(0.0001, 0.02))

qplot(as.numeric(variable), value, color=simulation, geom='line', 
      data=melt(theta2s, id.vars='simulation')) +
  geom_hline(yintercept=0.001, col='red') + 
  scale_y_continuous(trans=log10_trans())#, limits=c(0.0001, 0.02))


m12s <- cbind(simulation=factor(1:nrow(data)), data[,(2*no.epochs+1):(3*no.epochs)])
qplot(as.numeric(variable), value, color=simulation, geom='line', 
      data=melt(m12s, id.vars='simulation')) +
  geom_hline(yintercept=250, col='red') + 
  scale_y_continuous(trans=log10_trans())

m21s <- cbind(simulation=factor(1:nrow(data)), data[,(3*no.epochs+1):(4*no.epochs)])
qplot(as.numeric(variable), value, color=simulation, geom='line', 
      data=melt(m21s, id.vars='simulation')) +
  geom_hline(yintercept=250, col='red') + 
  scale_y_continuous(trans=log10_trans())#, limits=c(0.0001, 0.02))
