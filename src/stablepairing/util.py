### util.py ###

"""
utility/misc functions for parser, pairing and main scripts
"""

import pandas as pd
import numpy as np

def make_up_preferences(df, seed=1234, rank_cut=5):
    """
    make_up_preferences
    
    Makes up preferences for pairings between set B and A, given set A's preferences.
    The highly ranked members of B per individuals in A will also be highly
    (but randomly high) ranked by B. Lower ranked individuals recieve a random
    rank below the high rank tier. High rank vs low rank is thesholded by
    rank_cut (less than rank_cut are "highly ranked"). 
    Lower rank_cuts produce pairings strongly affected by A's preferences,
    but may yeild random results if many pairings are generated
    (say for "speed networking"). Higher rank_cuts will be more random, but
    allows for more pairings to be generated that reflect A's rankings.
    
    
    Inputs:
        df - pandas.DataFrame index set A, columns set B, values are rank (1 highest)
        seed - seed for random number generator (for reproducible shuffling), default 1234
        rank_cut - threshold below which individuals are considered "highly ranked"
                   default 5
    Output:
        df_new - pandas.DataFrame, preferences of set B, shape df.T
        
    """
    max_rank = np.max(df.max())
    mentors = list(df.columns)
    mentees = list(df.index)
    new_df = {}
    rng = np.random.default_rng(seed=seed)
    for mentor in mentors:
        mentees_ranked = list(df[df[mentor] < rank_cut].index)
        mentees_unranked = list(df[df[mentor] >= rank_cut].index)
        ranked_ranks = np.arange(1, len(mentees_ranked)+1, 1, dtype=int)
        unranked_ranks = np.arange(1, len(mentees_unranked)+1, 1, dtype=int) + len(mentees_ranked)
        rng.shuffle(ranked_ranks)
        rng.shuffle(unranked_ranks)
        new_df[mentor] = {}
        for mentee in mentees:
            if mentee in mentees_ranked:
                new_df[mentor][mentee] = ranked_ranks[mentees_ranked.index(mentee)]
            else:
                new_df[mentor][mentee] = unranked_ranks[mentees_unranked.index(mentee)]
    df_new = pd.DataFrame.from_dict(new_df, orient='index')
    return df_new

def remove_duplicates(df, check_column):
    """
    remove_duplicates
    
    Removes duplicate entries in a specific column. Chooses index with minimum
    NaN count or last index if if many minima to keep.
    
    Inputs
        df - pandas.Dataframe with columns with check_column in columns
        check_column - string column name to check for duplicates
    Output
        df - pandas.Dataframe with duplicates removed
    
    """
    duplicates = df.duplicated(subset=check_column, keep=False)
    if not(duplicates.empty): #If no duplicates do nothing
        duplicate_names = set(df[duplicates][check_column])
        idx2drop = [] # Collect duplicate indexes we don't want
        for dupe in duplicate_names:
            dupedf = df[df[check_column]==dupe].copy() #Copy to not add to original
            dupedf['NaN_count'] = dupedf.isnull().sum(axis='columns')
            min_nan = dupedf[::-1]['NaN_count'].idxmin() # Reversed so _last_ min
            idxs = list(dupedf.index)
            idxs.remove(min_nan) #We keep the min nan count/last index
            idx2drop.extend(idxs)
        df.drop(index=idx2drop, inplace=True)
    return df

def populate_nans(df):
    """
    populate_nans
    
    Fills nans in _numerical_ dataframe with max_value+1
    
    Input
        df - pandas.Dataframe with NaNs
    Output
        df - pandas.Dataframes with NaNs filled with max_value+1
    """
    fill_vals = df.max(axis='columns', skipna=True) + 1
    filldf = pd.concat([fill_vals.rename(col) for col in df.columns], axis='columns')
    filldf.fillna(value=len(filldf.columns), inplace=True) # in case someone is a jerk and doesn't actually fill preferences... (yes this happened)
    df.fillna(value=filldf, inplace=True)
    return df

def add_missing_persons(df, names, fillval=None):
    """
    add_missing_persons
    
    Takes a df with names as index, adds missing names to the bottom
    
    Inputs:
        df - pandas.Dataframe with some names in index
        names - iterable, complete list of names that should be in index
        fillval - default None, what value to fill with, if None is filled with len(names)
        
    Outputs:
        df - pandas.Dataframe with all names in index
    
    """
    if fillval is None:
        fillval = len(df.columns) #idk, large number for low preference of people who skipped survey?
    missing = set(names) - set(df.index)
    # Extra name parsing because sometime middle names are added or multiple last names (or tabs????)
    not_missing = set()
    for name in missing:
        for comparename in df.index:
            if is_same_name(name, comparename):
                not_missing.add(name)
    missing = missing - not_missing
    if len(missing) > 0:
        appenddf = pd.concat([pd.Series(fillval, index=df.columns, name=mis) for mis in missing], axis='columns')
        df = pd.concat([df, appenddf.T], axis=0)
    return df

def is_same_name(name1, name2):
    """
    is_same_name
    
    Compares if two names are the same.
    Looks for first name component of 1 to be in name 2
    also want last name component of 1 to be in 2 OR
    second to last name component of 1 to be in 2
    
    Inputs:
        name1 - string
        name2 - string
    Output:
        Bool, True if names match, False if not
    """
    allnames = disassemble_name(name1)
    firstmatch = allnames[0] in name2 #first name
    lastmatch = allnames[-1] in name2 #last (or last last) name
    if len(allnames) > 2:
        lastmatch2 = allnames[-2] in name2 #middle (or first last) name
    else:
        lastmatch2 = False
    return (firstmatch and (lastmatch or lastmatch2))

def disassemble_name(name):
    """
    disassemble_name
    
    splits name string into various part of name (first middle last last-last)
    
    Right now checks for spaces and tabs (\t)
    
    Input:
        name - string
    Output:
        allnames - list of strings with parts of name
    """
    name = name.replace('\t', ' ')
    splitname = name.split(' ')
    #allnames = []
    #for sname in splitname:
    #    allnames.extend(sname.split('\t')) #I've seen tabs in names :(
    return splitname

def unify_name_lists(namelist1, namelist2):
    """
    unify_name_lists
    
    Takes 2 lists of names and try to make duplicated names match
    checks for names by disassembling (splitting by spaces/tabe)
    then comparing if first and last or second last match
    if names are the same it choose the one with more elements
    
    Missing names are skipped.
    .replace('  ', ' ')
    Intended usage is to standardize name columns with equivlent name index
    
    Inputs:
        namelist1 - list of strings
        namelist2 - list of strings
    
    Outputs:
        renamelist1 - dict map with old namelist keys, unified names values
        renamelist2 - dict map with old namelist keys, unified names values
    """
    renamelist1 = {}
    renamelist2 = {}
    for i in range(len(namelist1)):
        for j in range(len(namelist2)):
            name1 = namelist1[i].replace('\t', ' ').replace('  ', ' ')
            name2 = namelist2[j].replace('\t', ' ')
            if is_same_name(name1, name2):
                allname1 = disassemble_name(name1)
                allname2 = disassemble_name(name2)
                if len(allname1) > len(allname2):
                    renamelist2[namelist2[j]] = name1
                    renamelist1[namelist1[i]] = name1
                else:
                    renamelist1[namelist1[i]] = name2
                    renamelist2[namelist2[j]] = name2
    return renamelist1, renamelist2

def fix_row(arr, rng=None):
    """
    fix_row

    Takes a row (array) of rankings and makes it so they are rankings
    1 through (len(arr)). Ranking order maintained. Duplicates are given
    shuffled adjacent numbers.
    IE [5,10,3,3,4,3] could become [5,6,2,3,4,1]

    Technical detail - to avoid creating new duplicate values when re-ranking
        this process shifts all of the values of the array to a large number
        if the original rankings are not in good faith (IE max(arr)>>len(arr))
        this function might fail.

    Inputs:
        arr - 1D numpy array of rankings
        rng - np.random.default_rng isntance. Default is None which will
              create one

    Output:
        arr - 1D numpy array with unique rankings

    """
    if rng is None:
        rng = np.random.default_rng(seed=1234)
    arr_shift = 10*len(arr) #large shift so we don't create new dupes in the process
    arr = arr - np.min(arr) + 1 + arr_shift #make min 1 + our shift, remove other shiftings
    sorted_arr = np.sort(arr) #sort to go from smallest (make 1) to largest
    count = 1 #start counting - first, smallest value should become 1
    uniques, cs = np.unique(sorted_arr, return_counts=True)
    for i in range(len(uniques)): #proceeding from smallest unique value
        u = uniques[i]
        c = cs[i]
        if u != count: # make u==count
            arr[arr==u] = count
        if c>1: #u is duplicated in array
            new_vals = np.arange(count, c+count, 1, dtype=int)
            rng.shuffle(new_vals) # shuffle shuffles in place
            arr[arr==count] = new_vals
        count += c #next value u should be
    return arr

def fix_rows(arr, rng=None):
    """
    fix_rows
    
    Fixes rows for a 2D array, see fix_row
    """
    if rng is None:
        rng = np.random.default_rng(seed=1234)
    for i in range(arr.shape[0]):
        arr[i,:] = fix_row(arr[i,:], rng=rng)
    return arr
