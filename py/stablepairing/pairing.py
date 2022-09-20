### pairing.py ###

'''
Implments the main class for the pairing algorithm.
Based on McVitte and Wilson 1970 (https://link.springer.com/content/pdf/10.1007/BF01934199.pdf)

Base functions of proposal, refusal and run are mostly straight from the paper,
except some tricky areas where the paper couldn't decide if it indexes by 0 or 1 and
we only index by zero here (so sometimes you'll see shifts of +/- 1 in the index, these
are important!).
'''

import numpy as np
import pandas as pd
import string
from .util import fix_row

# Note if comparing with the paper I have opted against using male/female and instead use A and B respectively

class StablePairing():
    '''
    Pairs 2 sets A and B with one another. The larger set will have 
    elements/people unpaired with the other set.
    
    This algorithm is optimal for set A and has stronger weight in the
    preferences of set A than other stable paired solutions (if they exist)
    
    Init takes 2 "choice" matricies, Achoice and Bchoice. Can be pandas.DataFrame or numpy.array.
    Rows are elements of A or B respectively, columns are elements of the other set.
    Values are the preference number, Achoice[i,j] == 1 means j from set B is i from set A's favorite choice.

    Note: the rows of A must correspond to the columns of B and vice-versa. This class checks that they
    have the right shape (Achoice.T.shape == Bchoice.shape) but externally you must ensure
    they are sorted the same way! With a dataframe one can simply sort alphabetically.
    '''
    def __init__(self, Achoice, Bchoice):
        assert type(Achoice) == type(Bchoice), "Achoice and Bchoice must be of the same type"
        if type(Achoice)==pd.core.frame.DataFrame:
            self.Achoice = Achoice.to_numpy() #note unlike in the paper I expect these indexed by 0, not by 1
            self.Anames = list(Achoice.index)
            self.Bchoice = Bchoice.to_numpy() #expect further index shifts (some arrays in paper are indexed by 0!)
            self.Bnames = list(Bchoice.index)
        else: #np array already, make up names AA-AB...ZY-ZZ
            self.Achoice = Achoice
            self.Anames = self.make_up_names(Achoice.shape[0], prefix='setA_')
            self.Bchoice = Bchoice
            self.Bnames = self.make_up_names(Bchoice.shape[0], prefix='setB_')
        assert self.Achoice.shape == self.Bchoice.T.shape, "Shape of Achoices must be the same as transposed Bchoices"
        # Note - with the name lists, that gives us the name of the i-th person
        self.num_A = len(self.Anames)
        self.num_B = len(self.Bnames)
        
        #"choice" matrix has values of preference rank, "rank" matrix has values of people number
        self.Arank = self.choice2rank(self.Achoice)
        self.match = None #this will be an array len(num_B) - indexed by zero so see -1 a lot in the index
        self.count = None
        self.Acounter = None
        self.Bc = None
        
    def _proposal(self, i):
        '''
        ith person in group A proposes pairing to the next (as stored in Acounter[i])
        person in group B. Calls refusal to determine outcome of proposal.
        
        Terminates when out of options, skips dummy in column 0.
        '''
        if (i != 0) and (self.Acounter[i] < (self.num_B)):
            self.count += 1 # number of proposals made
            # j here is not a person, but 1st, 2nd... so on choice of i (indexed by 0 :) )
            j = self.Acounter[i]
            self.Acounter[i] += 1
            self._refusal(i, self.Arank[i-1,j]) #Arank does not have dummy in 0, so shift i index back
        return

    def _refusal(self, i, j):
        '''
        Determines outcome of proposal of ith member of group A to jth member
        of group B. Accepts proposal if j ranks i higher than their current match.
        Then old match proposes to next in thier ranking. If i's proposal is rejected,
        i proposes match to next person in their rank.
        '''
        if self.Bc[j, self.match[j]] > self.Bc[j,i]:
            l = self.match[j]
            self.match[j] = i
            self._proposal(l)
        else:
            #print(f'woman {j} rejected man {i} in favor of current match {self.match[j]}')
            self._proposal(i)
        return
    
    def run(self):
        '''
        Loops through members of group A to propose matches to group B.
        Final matches are stored in self.match as a list indexed by members
        of group B with thier pairing to member of group A. -1 means unpaired
        member of group B.

        '''
        #Bc is Bchoice but with "dummy" in first column
        self.Bc = np.zeros((self.Bchoice.shape[0], self.Bchoice.shape[1]+1)) + 1000 #just large number to help spot bugs, should be overwritten
        self.Bc[:,0] = self.Bc.shape[1] + 1 #make sure dummy is low ranked and rejected
        self.Bc[:,1:] = self.Bchoice
        self. count = 0
        self.Acounter = np.zeros(self.num_A+1, dtype=int)
        self.match = np.zeros(self.num_B, dtype=int)
        for i in range(self.num_A+1): # +1 cause dummy in 0
            #print(f'man {i}, count is {self.count}')
            #print(self.Acounter)
            self._proposal(i)
        return
    
    def print_matches(self):
        '''
        print_matches

        Loops through matches and prints out names of matched pair.
        '''
        if self.match is not None:
            for i in range(len(self.match)):
                print(f'{self.Bnames[i]} is paired with {self.Anames[self.match[i]-1]}')
        else:
            print('Please call StablePairing.run() first!')


    def matches_as_series(self, orient='A', as_series=True):
        '''
        matches_as_series

        Outputs matches as a series or dictionary keys and values are names for the pair

        Inputs:
            orient - optional, 'A' or 'B', default 'A'. Orientation of series, 'A' orient will
                     have Anames as keys, Bnames as values. 'B' orient will flip this.
            as_series - bool, optional, default True. Return a pandas.Series if True,
                        else return a dictionary.
        '''
        assert self.match is not None, 'Please call StablePairing.run() first!'
        assert orient in ['A', 'B'], 'Orient must be "A" or "B" to indicate which is index!'
        matches = {}
        match_list = list(self.match-1) #index by zero...
        if orient == 'A':
            for i in range(len(self.Anames)):
                if i in match_list:
                    matches[self.Anames[i]] = self.Bnames[match_list.index(i)]
                else:
                    matches[self.Anames[i]] = 'None'
        elif orient == 'B':
            for i in range(len(self.Bnames)):
                if match_list[i] == -1: #no match
                    matches[self.Bnames[i]] = 'None'
                else:
                    matches[self.Bnames[i]] = self.Anames[match_list[i]]
        if as_series:
            return pd.Series(matches)
        return matches

    def evaluate_match(self):
        '''
        evaluate_match

        Returns a single number summarizing the goodness of match. 
        '''
        assert self.match is not None, 'Please call StablePairing.run() first!'
        print('Not yet implemented')
        return
    # In case you're unfamiliar, decorators (@xxxxxx) modify the function below it
    # This one, @staticmethod turns a function that is part of a class into
    # a static function, IE has no class dependence (no self arg) and does
    # not require the class to be instantiated
    @staticmethod
    def make_up_names(num, prefix=''):
        '''
        returns alphabetical names AA through ZZ
        
        Warning! Will fail if num > 26*26. IDK why you need so many though.
        
        This function is kinda dumb sorry.
        '''
        alpha = list(string.ascii_uppercase)
        names = []
        for a in alpha:
            for b in alpha:
                names.append(prefix+a+b)
        return names[:num]

    @staticmethod
    def choice2rank(parr, shuffleseed=1234):
        '''
        choice2rank

        Takes a "choice" array index i,j are people, values are preference
        to a "rank" array index i and values are people, index j is rank of preference
        
        min rank should be 1, will add 1 to correct
        
        Note: if parr has duplicate entries (equal choice number)
        calling rank2choice(choice2rank(parr)) will not give the
        original parr a ranking will be assigned for the unranked ones
        '''
        arr = parr.copy()
        if np.amin(arr) == 0:
            arr = arr+1
        rng = np.random.default_rng(seed=shuffleseed)
        rows = arr.shape[0]
        cols = arr.shape[1]
        # find duplicated rankings
        # max in each row are "unranked". Shuffle these.
        max_per_row = np.amax(arr, axis=1)
        ranked_per_row = np.count_nonzero((arr.T-max_per_row).T, axis=1) + 1
        new_arr = np.zeros(arr.shape, dtype=int) + 10000 # I dunno, large default val
        for i in range(rows):
            # fixed row meaning all duplicate values are shufled and ranks are unique
            # ints 1 through len(row). The nature of the "rank" array means some order needs to be chosen
            fixed_row = fix_row(arr[i,:], rng=rng)
            for j in range(cols):
                new_arr[i,j] = np.nonzero((fixed_row-1)==j)[0][0] #should only be one instance where this is true
        return new_arr
        ''' # somehow half this function go deleted so I re-wrote it - use version control early friends
            #u, c = np.unique(arr[i,:], return_counts=True)
            #dupes = u[c>1]
            #for dup in dupes:
            #    
            print(arr[i,:], max_per_row[i])
            unranked = np.nonzero(arr[i,:]==max_per_row[i])[0]
            rng.shuffle(unranked)
            for j in range(cols):
                if j < ranked_per_row[i] and not(len(unranked)==cols):
                    # minus 1 because ranking is 1 to n, indexing is 0
                    new_arr[i,j] = np.nonzero((arr[i,:]-1)==j)[0][0] #should only be one instance where this is true
                else:
                    # Weird if else because of slicing
                    if j==0:
                        new_arr[i,:] = unranked
                    else:
                        new_arr[i,j-1:] = unranked
                    #We're done with this row
                    break
        '''

    @staticmethod
    def rank2choice(parr):
        '''
        Converts "rank" matrix to "choice" matrix. See choice2rank.
        '''
        arr = parr.copy() # don't edit the OG
        # convert to index by 0 if not already
        if np.amin(arr) == 1:
            arr = arr - 1
        arr2 = np.zeros(arr.shape, dtype=int) + 1000
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                arr2[i, j] = np.nonzero(arr[i, :]==j)[0]
        return arr2 + 1 # we like minimum choice number to be 1