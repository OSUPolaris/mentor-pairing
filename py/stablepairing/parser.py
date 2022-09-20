### parser.py ###

'''
Contains parsers for qualtrics surveys ran by polaris that surve as input
data for pairing. 

If you are using this outside of polaris this may not be very useful unless
you have a survey of a similar format. This could also serve as a reference
for writing a parser for a different survey.
'''

import pandas as pd
import numpy as np
from .util import remove_duplicates, populate_nans, unify_name_lists, add_missing_persons

def survey_res_parser(survey_file, has_double_up_q=True):
    '''
    survey_res_parser
    
    Parses result of qualtrics ranking survey into lean, usable format.
    
    Inputs:
        survey_file - string or os.path pointing to csv output of qualtrics survey
        has_double_up_q - bool, default=True, if survey asks mentors if they're ok with
                          being doubled up with mentees (right now just removes q, doesn't use it)
                          
    Outputs:
        mentor_df - pandas.DataFrame with mentor names as index, mentee names as columns
                    and mentor rankings of mentees as values
        mentee_df - pandas.DataFrame with mentee names as index, mentor names as columns
                    and mentee rankings of mentors as values
    '''
    
    ### Step 1. Read and remove columns we don't ever need
    df = pd.read_csv(survey_file)
    # This below is gross hardcoding. I want some of this creep info explicitly removed, though another line will also remove these
    columns_to_drop = ['StartDate','EndDate','Status','IPAddress','Progress','Duration (in seconds)','RecordedDate','ResponseId','RecipientLastName','RecipientFirstName','RecipientEmail','ExternalReference','LocationLatitude','LocationLongitude','DistributionChannel','UserLanguage']
    df.drop(columns=columns_to_drop, inplace=True)
    
    ### Step 2. Get columns of certain questions (some of these change simply because # of students changes)
    # This extracts a pd.series (effectively a dict), 0th row is the question text
    q_row = df.iloc[0]
    # Now prepare some data for column parsing
    # These are populated by generic names like Q4 (question 4?) or Q35_26 (question 35, choice 26?) made up by qualtrics
    mentor_columns = {}
    mentee_columns = {}
    which_key = None #column for mentee or mentor Q
    double_up_key = None #column for if mentor is ok with being doubled up
    name_select_keys = [] #columns for name select (one is mentors, one is mentees)
    # Iterate through questions to extract a few column names for later cleaning
    # A lot of this parsing is gross hardcoding that needs to change if the survey wording changes
    for key, value in q_row.items():
        if 'mentee (' in value:
            # dash space is very helpful for splitting name from other text DO NOT change this in the survey!!!
            mentee_columns[key] = value.split('- ')[-1].replace('\t', ' ').replace('  ', ' ') #tabs for some reason often appear?
        elif 'mentor (' in value:
            mentor_columns[key] = value.split('- ')[-1].replace('\t', ' ').replace('  ', ' ')
        if 'Are you a mentee or a mentor?' in value: #note this needs to be changed if question is reworded
            which_key = key
        if has_double_up_q and ('Are you comfortable having two mentees?' in value): #Again watch for q wording change
            double_up_key = key
        if value == 'Select your name': #Maybe change survey to make these not identical?
            name_select_keys.append(key)
    # Some asserts to fail gracefully if survey format changed
    assert len(name_select_keys)==2, 'Must be a column for mentor name select and another column for mentee name select'
    assert which_key is not None, 'Must be a column asking if they are a mentor or mentee!'
    if has_double_up_q:
        assert double_up_key is not None, 'Must ask mentors if they are ok with being doubled up'
    
    ### Step 3. Split off mentor dataframe
    df = df[df['Finished']=='True'].copy() #pop all not finished
    # Split off mentor dataframe
    mentor_df = df[df[which_key] == 'Mentor'].copy()
    mentor_df.rename(columns=mentee_columns, inplace=True)
    # Sort out which name select is for which group, only need to check once (and not duplicate check for mentees)
    if len(set(mentor_df[name_select_keys[0]]))==1: # Weird check but only time they are all identical is when column is all NaN
        mentor_name_key = name_select_keys[1]
        mentee_name_key = name_select_keys[0]
    else: # Note index flip between above and below, if not one way it is the other way
        mentor_name_key = name_select_keys[0]
        mentee_name_key = name_select_keys[1]
    mentor_drop = list(mentor_columns.keys())
    mentor_drop.extend(['Finished', which_key, double_up_key, mentee_name_key])
    mentor_df.drop(columns=mentor_drop, inplace=True)
    # remove NaN (no names, supposedly a survey can be "finished" with still no name)
    mentor_df = mentor_df[mentor_df[mentor_name_key].notna()].copy()
    
    ### Step 4. Now split off mentee dataframe
    mentee_df = df[df[which_key]=='Mentee'].copy()
    mentee_df.rename(columns=mentor_columns, inplace=True)
    mentee_drop = list(mentee_columns.keys())
    mentee_drop.extend(['Finished', which_key, double_up_key, mentor_name_key])
    mentee_df.drop(columns=mentee_drop, inplace=True)
    mentee_df = mentee_df[mentee_df[mentee_name_key].notna()].copy()
    
    ### Step 5. Clear duplicates
    # response with fewest NaNs is accepted, or last response if same num NaN
    # Qualtrics output sorts by complete or not, then by time completed, so last response is newest
    mentor_df = remove_duplicates(mentor_df, mentor_name_key)
    mentee_df = remove_duplicates(mentee_df, mentee_name_key)
    # With duplicates cleared set index to names
    mentor_df.set_index(mentor_name_key, inplace=True)
    mentee_df.set_index(mentee_name_key, inplace=True)
    # Now covert "object" (string) columns to floats (floats because NaNs) 
    # since all values are numerical after names moved to index
    mentor_df = mentor_df.astype(np.float64)
    mentee_df = mentee_df.astype(np.float64)
    
    ### Step 6. Replace NaNs with numbers
    mentor_df = populate_nans(mentor_df)
    mentee_df = populate_nans(mentee_df)
    # Just to be clean we can go to ints now
    mentor_df = mentor_df.astype(int)
    mentee_df = mentee_df.astype(int)
    
    ### Step 7. Unify names (remove extraneous chars, use all parts if one set is missing some)
    #be careful 'mentee_cols' has the names of mentors but is called such because it is part of the mentee_df
    mentor_index, mentee_cols = unify_name_lists(list(mentor_df.index), list(mentee_df.columns))
    mentee_index, mentor_cols = unify_name_lists(list(mentee_df.index), list(mentor_df.columns))
    mentor_df.rename(mentor_index, inplace=True, axis='index')
    mentor_df.rename(mentor_cols, inplace=True, axis='columns')
    mentee_df.rename(mentee_index, inplace=True, axis='index')
    mentee_df.rename(mentee_cols, inplace=True, axis='columns')
    
    ### Step 8. Fill in missing mentees/mentors
    # columns (prewritten in the survey) have the "complete" mentee/mentor name lists
    mentor_df = add_missing_persons(mentor_df, mentee_df.columns)
    mentee_df = add_missing_persons(mentee_df, mentor_df.columns)
    
    return mentor_df, mentee_df


def intro_survey_parser(survey_file):
    '''
    survey_res_parser
    
    Parses result of qualtrics ranking survey into lean, usable format.
    Inputs:
        survey_file - string or os.path pointing to csv output of qualtrics survey
                          
    Outputs:
        clean_df - pandas.DataFrame cleaned up
    '''
    
    ### Step 1. Read and remove columns we don't ever need
    df = pd.read_csv(survey_file)
    # This below is gross hardcoding. I want some of this creep info explicitly removed, though another line will also remove these
    columns_to_drop = ['StartDate','EndDate','Status','IPAddress','Progress','Duration (in seconds)','RecordedDate','ResponseId','RecipientLastName','RecipientFirstName','RecipientEmail','ExternalReference','LocationLatitude','LocationLongitude','DistributionChannel','UserLanguage']
    df.drop(columns=columns_to_drop, inplace=True)
    
    ### Step 2. Get columns of certain questions (some of these change simply because # of students changes)
    # This extracts a pd.series (effectively a dict), 0th row is the question text
    q_row = df.iloc[0]
    # Now prepare some data for column parsing
    # These are populated by generic names like Q4 (question 4?) or Q35_26 (question 35, choice 26?) made up by qualtrics
    mentor_columns = {}
    first_name_col = None
    last_name_col = None
    # Iterate through questions to extract a few column names for later cleaning
    # A lot of this parsing is gross hardcoding that needs to change if the survey wording changes
    for key, value in q_row.items():
        if 'Which mentors do you want to meet with?' in value:
            name = value.split('- ')[-1].replace('\t',' ')
            # dash space is very helpful for splitting name from other text DO NOT change this in the survey!!!
            mentor_columns[key] = name
        if '- First' in value:
            first_name_col = key
        if '- Last' in value:
            last_name_col = key
    # Some asserts to fail gracefully if survey format changed
    assert first_name_col is not None, 'Did not find first name column!'
    assert last_name_col is not None, 'Did not find last name column!'
    
    ### Step 3. Split off mentor dataframe
    df = df[df['Finished']=='True'] #pop all not finished
    # Split off mentor dataframe
    ret_df = df.copy()
    ret_df.rename(columns=mentor_columns, inplace=True)
    ret_df['name'] = ret_df[first_name_col] + ' ' + ret_df[last_name_col]
    keep_cols = ['name']
    keep_cols.extend(list(mentor_columns.values()))
    drop_cols = set(ret_df.columns) - set(keep_cols)
    ret_df.drop(columns=drop_cols, inplace=True)
    
    ### Step 4. Clear duplicates
    # response with fewest NaNs is accepted, or last response if same num NaN
    # Qualtrics output sorts by complete or not, then by time completed, so last response is newest
    ret_df = remove_duplicates(ret_df, 'name')
    # With duplicates cleared set index to names
    ret_df.set_index('name', inplace=True)
    # Now covert "object" (string) columns to floats (floats because NaNs) 
    # since all values are numerical after names moved to index
    ret_df = ret_df.astype(np.float64)
    
    ### Step 5. Replace NaNs with numbers
    max_rank = len(ret_df.columns)
    ret_df = ret_df.fillna(value=max_rank) #populate_nans(ret_df)
    # Just to be clean we can go to ints now
    ret_df = ret_df.astype(int)
    # reverse ranking, survey has 10 highest, 1 lowest, put 0s to large val
    replace_map = {0:max_rank}
    for i in range(1,11):
        replace_map[i] = 11-i
    # or if nans are 0s for some reason
    ret_df = ret_df.replace(replace_map)
    
    ### Step 6. Fill in missing mentees/mentors
    # columns (prewritten in the survey) have the "complete" mentee/mentor name lists
    #mentor_df = add_missing_persons(mentor_df, mentee_df.columns)
    # Maybe do this manually instead? Or have to pass a list of all names (that match with preferred names... :/)
    
    return ret_df