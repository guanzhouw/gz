#!/usr/bin/env python
from __future__ import print_function, division

""" 
Mnemonic Similarity Task in PsychoPy

Copyright 2017, Craig Stark

Forked from v0.95 of the C++ version of MST on July 28, 2017

8/9/17: First solidly-working version (standard study-test)

1/6/18: Forked off to make the continuous version.  This will work well so 
  long as you're not trying to use multiple sets in one run.  It works off
  of data files generated by some Matlab code in LagGenerator.  That code
  creates text files that describe what stimuli should come up when.  Here,
  we just follow that order of stimuli.
  
  Does not allow using portions of each set (the subset option in the normal
  version).
  
  Currently, we have 2 "all-short" variants in place that are slightly different
  in makeup.
  
  Expects to have the standard Set N stimulus directories and to use only the
    stimuli in here (limiting the length of the run we can do a bit)
  Assumes the # of repeat and lure pairs are the same
  
  Includes self-paced and other edits from 1/7 MST_Psychopy.py

1/7/21  (CELS): Log file output bugs fixed
  
  
6/1/23 (CELS): Updated for current PsychoPy / Python3
6/2/23 (CELS): Customized for the Eich lab fMRI experiment that uses the 
320-length order files. These are different in that there are no separate foils
(not needed really), 100 lures, and 60 repeats. 
- One thing that's a bit of a kludge here is that the prior versions assumed a 
max of 64 per trial type and here we are using 100 lures. Ideally, the code in 
setup_list_permuted would detect this from the order file and allocate 
accordingly. The original used 64 here as a fixed length of each list. But, 
time is short and I've just manually fixed the lure length to 100 to get things 
up and going.
- Also, set the default timing to 3 + 0.5s
6/19/23 (CELS): Fixed to allow 100 lures rather than 99.
  - Fixed Corr/RT header bug
6/26/23 (CELS): Set to split into 4 blocks
"""

"""
TBD:
- Touch box responses
"""

import numpy as np
import csv
import os
from psychopy import visual, core, data, tools, event
from psychopy import gui
from datetime import datetime
from scipy.stats import norm

def get_parameters(skip_gui=False):
    # Setup my global parameters
    try:#try to get a previous parameters file 
        param_settings = tools.filetools.fromFile('lastParams_MSTCont.pickle')
        last_entry=param_settings[12] # Make sure we have enough entries in here
    except:
        param_settings = [1234,3.0,0.5,'Set_320',1,'1','1VC','2B','3NM',False,False,-1,['1']]
    #print(param_settings)    
    if not skip_gui:
        param_dialog = gui.Dlg('Experimental parameters')
        param_dialog.addField('ID',param_settings[0],tip='Must be numeric only')
        param_dialog.addField('Duration',param_settings[1])
        param_dialog.addField('ISI',param_settings[2])
        param_dialog.addField('Lag set', choices=['AllShort_Set1','AllShort_Set2','Set_80x4'],initial=param_settings[3])
        param_dialog.addField('Order',param_settings[4])
        param_dialog.addField('Set', choices=['1','2','3','4','5','6','C','D','E','F','ScC'],initial=param_settings[5])
        param_dialog.addField('Resp 1 keys',param_settings[6])
        param_dialog.addField('Resp 2 keys',param_settings[7])
        param_dialog.addField('Resp 3 keys',param_settings[8])
        param_dialog.addField('Self-Paced', initial=param_settings[9])
        param_dialog.addField('Two-Choice', initial=param_settings[10])
        param_dialog.addField('Randomization',param_settings[11],tip='-1=Use ID, 0=Use time, >0 = Use specific seed')
        param_dialog.addField('Block', choices=['1','2','3','4'],initial=param_settings[12])
        param_settings=param_dialog.show()
        #print(ok_data)
        if param_dialog.OK:
            tools.filetools.toFile('lastParams_MSTCont.pickle', param_settings)
            params = {'ID': param_settings[0],
                  'Duration': param_settings[1],
                  'ISI':param_settings[2],
                  'LagSet': param_settings[3],
                  'Order':param_settings[4],
                  'Set': param_settings[5],
                  'Resp1Keys':param_settings[6],
                  'Resp2Keys':param_settings[7],
                  'Resp3Keys':param_settings[8],
                  'SelfPaced': param_settings[9],
                  'TwoChoice': param_settings[10],
                  'Randomization':param_settings[11],
                  'Block': param_settings[12]}
        else:
            core.quit()
    else:
        params = {'ID': param_settings[0],
                  'Duration': param_settings[1],
                  'ISI':param_settings[2],
                  'LagSet': param_settings[3],
                  'Order':param_settings[4],
                  'Set': param_settings[5],
                  'Resp1Keys':param_settings[6],
                  'Resp2Keys':param_settings[7],
                  'Resp3Keys':param_settings[8],
                  'SelfPaced': param_settings[9],
                  'TwoChoice': param_settings[10],
                  'Randomization':param_settings[11],
                  'Block': param_settings[12] }
 
    return params


  
def check_files(SetName):
    """ 
    SetName should be something like "C" or "1"
    Checks to make sure there are the right #of images in the image directory
    Loads the lure bin ratings into the global set_bins list and returns this
    """
    import glob
    import os

    #print(SetName)
    #print(P_N_STIM_PER_LIST)
    
    bins = []  # Clear out any existing items in the bin list
    
    # Load the bin file
    with open("Set"+str(SetName)+" bins.txt","r") as bin_file:
        reader=csv.reader(bin_file,delimiter='\t')
        for row in reader:
            if int(row[0]) > 192:
                raise ValueError('Stimulus number ({0}) too large - not in 1-192 in binfile'.format(row[0]))
            if int(row[0]) < 1:
                raise ValueError('Stimulus number ({0}) too small - not in 1-192 in binfile'.format(row[0]))
            bins.append(int(row[1]))
    if len(bins) != 192:
        raise ValueError('Did not read correct number of bins in binfile')
    
    # Check the stimulus directory
    img_list=glob.glob("Set " +str(SetName) + os.sep + '*.jpg')
    if len(img_list) < 384:
        raise ValueError('Not enough files in stimulus directory {0}'.format("Set " +str(SetName) + os.sep + '*.jpg'))
    for i in range(1,193):
        if not os.path.isfile("Set " +str(SetName) + os.sep + '{0:03}'.format(i) + 'a.jpg'):
            raise ValueError('Cannot find: ' + "Set " +str(SetName) + os.sep + '{0:03}'.format(i) + 'a.jpg')
        if not os.path.isfile("Set " +str(SetName) + os.sep + '{0:03}'.format(i) + 'b.jpg'):
            raise ValueError('Cannot find: ' + "Set " +str(SetName) + os.sep + '{0:03}'.format(i) + 'b.jpg')
    return bins

def load_and_decode_order(repeat_list,lure_list,foil_list,
                          lag_set='AllShort_Set2',order=1,base_dir='LagGenerator',
                          stim_set='1',verbose=False):
    """
    Loads the order text file and decodes this into a list of image names, 
     conditions, lags, etc.
    
    lag_set: Directory name with the order files
    order: Which order file to use (numeric index)
    base_dir: Directory that holds the set of lag sets
    stim_set = Set we're using (e.g., '1', or 'C')
    repeat_list,lure_list,foil_list: Lists (np.arrays actually) created by setup_list_permuted
    

    In the order files files we have 2 columns:
        1st column is the stimulus type + number:
        Offset_1R = 0; % 1-100 1st of repeat pair
        Offset_2R = 100; % 101-200  2nd of repeat pair
        Offset_1L = 200; % 201-300 1st of lure pair
        Offset_2L = 300; % 301-400 2nd of lure pair
        Offset_Foil = 400; % 401+ Foil
        
        2nd column is the lag + 500 (-1 for 1st and foil)

    Returns:
        lists / arrays that are all N-trials long
        
        type_code: 0=1st of repeat
                   1=2nd of repeat
                   2=1st of lure
                   3=2nd of lure
                   4=foil
        ideal_resp: 0=old
                    1=similar
                    2=new
        lag: Lag for this item (-1=1st/foil, 0=adjacent, N=items between)
        fnames: Actual filename of image to be shown
    """
    #verbose=True
    fname=base_dir + os.sep + lag_set + os.sep + "order_{0}.txt".format(order)
    if verbose:
        print('loading',fname)
    fdata=np.genfromtxt(fname,dtype=int,delimiter=',')
    
    lag = fdata[:,1]
    lag[lag != -1] = lag[lag != -1] - 500
    
    type_code = (fdata[:,0]-1)//100  #Note, this works b/c we loaded the data as ints
    
    stim_index = fdata[:,0]-100*type_code
    
    ideal_resp = np.zeros_like(stim_index)
    ideal_resp[type_code==4]=2
    ideal_resp[type_code==0]=2
    ideal_resp[type_code==2]=2
    ideal_resp[type_code==1]=0
    ideal_resp[type_code==3]=1
    
    fnames=[]
    dirname='Set {0}{1}'.format(stim_set, os.sep)  # Get us to the directory
    for i in range(len(type_code)):
        stimfile='UNKNOWN'
        if verbose:
            print(i,type_code[i],stim_index[i]-1)
        if type_code[i]==0 or type_code[i]==1:
            stimfile='{0:03}a.jpg'.format(repeat_list[stim_index[i]-1])
        elif type_code[i]==2:
            stimfile='{0:03}a.jpg'.format(lure_list[stim_index[i]-1])
        elif type_code[i]==3:
            stimfile='{0:03}b.jpg'.format(lure_list[stim_index[i]-1])
        elif type_code[i]==4:
            stimfile='{0:03}a.jpg'.format(foil_list[stim_index[i]-1])
        fnames.append(dirname+stimfile)
    
    return (type_code,ideal_resp,lag,fnames)
    
    
def setup_list_permuted(set_bins):
    """
    set_bins = list of bin values for each of the 192 stimuli -- set specific
    
    Assumes check_files() has been run so we have the bin numbers for each stimulus

    Returns lists with the image numbers for each stimulus type (study, repeat...)
    in the to-be-used permuted order. Full 64 given for all.  This will get
    cut down and randomized in create_order()
    
    6/2/23: Revised to allow for 100 lures in an imbalanced design

    """

    
    if len(set_bins) != 192:
        raise ValueError('Set bin length is not the same as the stimulus set length (192)')

    
    # Figure the image numbers for the lure bins
    lure1=np.where(set_bins == 1)[0] + 1
    lure2=np.where(set_bins == 2)[0] + 1
    lure3=np.where(set_bins == 3)[0] + 1
    lure4=np.where(set_bins == 4)[0] + 1
    lure5=np.where(set_bins == 5)[0] + 1
    
    # Permute these
    lure1 = np.random.permutation(lure1)
    lure2 = np.random.permutation(lure2)
    lure3 = np.random.permutation(lure3)
    lure4 = np.random.permutation(lure4)
    lure5 = np.random.permutation(lure5)
    
    maxlures=100
    lures = np.empty(maxlures,dtype=int)
    # Make the Lure list to go L1, 2, 3, 4, 5, 1, 2 ... -- 64 total of them (max)
    lure_count = np.zeros(5,dtype=int)
    nonlures = np.arange(1,193,dtype=int)
    for i in range(maxlures):  
        if i % 5 == 0:
            lures[i]=lure1[lure_count[0]]
            lure_count[0]+=1
        elif i % 5 == 1:
            lures[i]=lure2[lure_count[1]]
            lure_count[1]+=1
        elif i % 5 == 2:
            lures[i]=lure3[lure_count[2]]
            lure_count[2]+=1
        elif i % 5 == 3:
            lures[i]=lure4[lure_count[3]]
            lure_count[3]+=1
        elif i % 5 == 4:
            lures[i]=lure5[lure_count[4]]
            lure_count[4]+=1
        nonlures=np.delete(nonlures,np.argwhere(nonlures == lures[i]))
            
    # Randomize the non-lures and split into 64-length repeat, whatever left goes to foils
    nonlures=np.random.permutation(nonlures)
    repeats = nonlures[0:64]
    foils = nonlures[64:]
           
    # At this point, we're full 64-item length lists for everything
    # break this down into the right size
    #repeatstim=repeats[0:set_size]
    #lurestim=lures[0:set_size]
    #foilstim=foils[0:set_size]
    
    # Our lures are still in L1, 2, 3, 4, 5, 1, 2, ... order -- fix that
    #lurestim=np.random.permutation(lurestim)
            
    
    return (repeats,lures,foils)
    


def decode_response(params,response):
    if params['Resp1Keys'].lower().find(response.lower()) >= 0:
        respcode = 1
    elif params['Resp2Keys'].lower().find(response.lower()) >= 0:
        respcode = 2
    elif params['Resp3Keys'].lower().find(response.lower()) >= 0:
        respcode = 3
    elif response == '5':  # Scanner trigger
        respcode = 99
    elif response in ['escape','esc']:
        respcode = -1
    return respcode
    



def show_task(params,fnames,type_code,lag,set_bins,nblocks=4):
    """
    params: structure with all the expeirmental parameters
    fnames: list of filenames to show in order (from load_and_decode_order)
    type_code: Trial type numeric code (see load_and_decode_order)
    lag: # of intervening items b/n 1st and second (from load_and_decode_order)
    set_bins: lure-bin number (only relevant if it's a lure)

    """
    
    global log, win
    total_trials=len(fnames)
    trials_per_block=total_trials // nblocks 
    start_index=trials_per_block * (int(params['Block']) - 1)
    print(total_trials,trials_per_block,start_index)
    if params['TwoChoice']==True:
        instructions1=visual.TextStim(win,text="Old or New?",pos=(0,0.9),
            color=(-1,-1,-1),wrapWidth=1.75,anchorHoriz='center',anchorVert='center')
    else:
        instructions1=visual.TextStim(win,text="Old, Similar, or New?",pos=(0,0.9),
            color=(-1,-1,-1),wrapWidth=1.75,anchorHoriz='center',anchorVert='center')
    
    instructions2=visual.TextStim(win,text="Press the spacebar to begin",pos=(0,-0.25),
        color=(-0.5,-0.5,-0.5),wrapWidth=1.75,anchorHoriz='center',anchorVert='center')
    
    instructions1.draw()
    instructions2.draw()
    win.flip()
    key = event.waitKeys(keyList=['space','5','esc','escape'])
    if key and key[0] in ['escape','esc']:
        print('Escape  hit - bailing')
        return -1
    TLF_trials = np.zeros(3)  # Number of trials of each type we have a response to
    TLF_response_matrix = np.zeros((3,3))  # Rows = O,(S),N  Cols = T,L,R
    lure_bin_matrix = np.zeros((4,5)) # Rows: O,S,N,NR  Cols=Lure bins
    
    log.write('Task started at {0}\n'.format(str(datetime.now())))
    log.write('Trial,Stim,Cond,Lag,LBin,StartT,Resp,Corr,RT\n')
    local_timer = core.MonotonicClock()
    duration = params['Duration']
    isi = params['ISI']
    ncorrect = 0
    log.flush()
    valid_keys = list(params['Resp1Keys'].lower()) + list(params['Resp2Keys'].lower()) + list(params['Resp3Keys'].lower()) + ['esc','escape']
    
    for trial in range(trials_per_block):
        stim_index=trial+start_index
        print(trial,stim_index,fnames[stim_index])
        if params['SelfPaced']:
            t1=local_timer.getTime()
        else:
            t1 = trial * (duration + isi)  # Time when this trial should have started
        stim_path = fnames[stim_index]
        stim_number = int(stim_path[-8:-5])
        log.write('{0},{1},{2},{3},{4},{5:.3f},'.format(stim_index+1,fnames[stim_index],
                  type_code[stim_index],lag[stim_index],set_bins[stim_number-1],local_timer.getTime()))
        log.flush()
        image = visual.ImageStim(win, image=fnames[stim_index])
        image.draw()
        instructions1.draw()
        win.flip()
        response = 0
        correct = 0
        RT=0
        key = event.waitKeys(duration,keyList=valid_keys)  # Wait our normal duration
        if key and key[0] in ['escape','esc']:
                print('Escape hit - bailing')
                log.write('\nEscape key aborted experiment\n')
                return -1
        elif key:
            RT=local_timer.getTime() - t1
            core.wait(t1 + duration - local_timer.getTime()) # Wait the remainder of the trial
        win.flip() # Clear the screen for the ISI
        if params['SelfPaced'] and (RT < 0.05):  # Continue waiting until we get something
            key = event.waitKeys(keyList=valid_keys)
            RT=local_timer.getTime() - t1
        if params['SelfPaced']:
            core.wait(isi)
        else:  # Do the ISI locking to the clock cleaning and allow a response in it if we don't have one
            while local_timer.getTime() < (t1 + duration + isi):
                if (RT < 0.05):
                    key = event.getKeys(keyList=valid_keys)
                    if key:
                        RT=local_timer.getTime() - t1
        if RT > 0.05: # We have a response
            response = decode_response(params,key[0])
            # Increment the appropriate trial type counter (for count of # they responded to)
            if type_code[stim_index]==1:    # Repeatitions -- 2nd of real repeat
                TLF_trials[0] += 1
                trial_type = 1
            elif type_code[stim_index]==3:  # Lure 2nd presentations
                TLF_trials[1] += 1
                trial_type = 2
            else:  # All others -- 1st of 2 and extra foils are firsts
                TLF_trials[2] += 1
                trial_type = 3
            TLF_response_matrix[response-1,trial_type-1] += 1  # Increment the response x type  matrix as needed
            if params['TwoChoice']==True:  # Old/new variant
                if trial_type == 1 and response == 1:  # Hit
                    correct=1
                elif trial_type == 2 and response == 2:  #Lure-CR
                    correct=1
                elif trial_type == 3 and response == 2:  #CR
                    correct=1
            else:  #Old/similar/new variant
                if trial_type == 1 and response == 1:  # Hit
                    correct=1
                elif trial_type == 2 and response == 2:  #Lure-Similar
                    correct=1
                elif trial_type == 3 and response == 3:  #CR
                    correct=1
            log.write('{0},{1},{2:.3f}\n'.format(response,correct,RT))
        else:
            log.write('NA\n')
        if type_code[stim_index] == 3:  # A 2nd of lure pair - Take care of the lure-bin details
            bin_index = set_bins[stim_number-1] - 1  # Make it 0-indexed
            resp_index = response - 1  # Make this 0-indexed
            if resp_index == -1:
                resp_index = 3  # Loop the no-responses into the 4th entry here
            lure_bin_matrix[resp_index,bin_index] += 1
        win.flip() # Clear the screen for the ISI
        while local_timer.getTime() < (t1 + duration + isi):
            key = event.getKeys()
            #print(key)
            if key and key[0] in ['escape','esc']:
                print('Escape hit - bailing')
                log.write('\nEscape key aborted experiment\n')
                return -1
        ncorrect += correct
    # Print some summary stats to the log file
    log.write('\nValid responses:\nTargets, {0:.0f}\nlures, {1:.0f}\nfoils, {2:.0f}'.format(TLF_trials[0],TLF_trials[1],TLF_trials[2]))
    log.write('\nCorrected rates\n')
    log.write('\nRateMatrix,Targ,Lure,Foil\n')
    # Fix up any no-response cell here so we don't divide by zero
    TLF_trials[TLF_trials==0.0]=0.00001
    log.write('Old,{0:.2f},{1:.2f},{2:.2f}\n'.format(
        TLF_response_matrix[0,0] / TLF_trials[0], 
        TLF_response_matrix[0,1] / TLF_trials[1],
        TLF_response_matrix[0,2] /  TLF_trials[2]))
    log.write('Similar,{0:.2f},{1:.2f},{2:.2f}\n'.format(
        TLF_response_matrix[1,0] / TLF_trials[0], 
        TLF_response_matrix[1,1] / TLF_trials[1],
        TLF_response_matrix[1,2] /  TLF_trials[2]))
    log.write('New,{0:.2f},{1:.2f},{2:.2f}\n'.format(
        TLF_response_matrix[2,0] / TLF_trials[0], 
        TLF_response_matrix[2,1] / TLF_trials[1],
        TLF_response_matrix[2,2] /  TLF_trials[2]))

    log.write('\nRaw counts')
    log.write('\nRawRespMatrix,Targ,Lure,Foil\n')
    log.write('Old,{0:.0f},{1:.0f},{2:.0f}\n'.format(TLF_response_matrix[0,0], TLF_response_matrix[0,1],TLF_response_matrix[0,2]))
    log.write('Similar,{0:.0f},{1:.0f},{2:.0f}\n'.format(TLF_response_matrix[1,0], TLF_response_matrix[1,1],TLF_response_matrix[1,2]))
    log.write('New,{0:.0f},{1:.0f},{2:.0f}\n'.format(TLF_response_matrix[2,0], TLF_response_matrix[2,1],TLF_response_matrix[2,2]))
    
    log.write('\n\nLureRawRespMatrix,Bin1,Bin2,Bin3,Bin4,Bin5\n')
    log.write('Old,{0:.0f},{1:.0f},{2:.0f},{3:.0f},{4:.0f}\n'.format(
        lure_bin_matrix[0,0], lure_bin_matrix[0,1],lure_bin_matrix[0,2],lure_bin_matrix[0,3],lure_bin_matrix[0,4]))
    log.write('Similar,{0:.0f},{1:.0f},{2:.0f},{3:.0f},{4:.0f}\n'.format(
        lure_bin_matrix[1,0], lure_bin_matrix[1,1],lure_bin_matrix[1,2],lure_bin_matrix[1,3],lure_bin_matrix[1,4]))
    log.write('New,{0:.0f},{1:.0f},{2:.0f},{3:.0f},{4:.0f}\n'.format(
        lure_bin_matrix[2,0], lure_bin_matrix[2,1],lure_bin_matrix[2,2],lure_bin_matrix[2,3],lure_bin_matrix[2,4]))
    log.write('NR,{0:.0f},{1:.0f},{2:.0f},{3:.0f},{4:.0f}\n'.format(
        lure_bin_matrix[3,0], lure_bin_matrix[3,1],lure_bin_matrix[3,2],lure_bin_matrix[3,3],lure_bin_matrix[3,4]))

    log.write('\nPercent-correct (corrected),{0:.2}\n'.format(ncorrect / TLF_trials.sum()))
    log.write('Percent-correct (raw),{0:.2}\n'.format(ncorrect / len(fnames)))

    hit_rate = TLF_response_matrix[0,0] / TLF_trials[0]
    false_rate = TLF_response_matrix[0,2] / TLF_trials[2]
    log.write('\nCorrected recognition (REC) (p(Old|Target)-p(Old|Foil)), {0:.2f}'.format(hit_rate - false_rate))

    if params['TwoChoice']==True:
        log.write('\nTwo-choice test metrics\n')
        lure_rate = TLF_response_matrix[0,1] / TLF_trials[1]
        if hit_rate == 0.0:
            hit_rate = 0.5 / TLF_trials[0]
        if false_rate == 0.0:
            false_rate = 0.5 / TLF_trials[2]
        if lure_rate == 0.0:
            lure_rate = 0.5 / TLF_trials[1]
            
        log.write('Endorsement rates')
        log.write('Targets: {0:.2f}'.format(hit_rate))
        log.write('Lures: {0:.2f}'.format(lure_rate))
        log.write('Foils and Firsts: {0:.2f}'.format(false_rate))
        
        
        dpTF = norm.ppf(hit_rate) - norm.ppf(false_rate)
        dpTL = norm.ppf(hit_rate) - norm.ppf(lure_rate)
        dpLF = norm.ppf(lure_rate) - norm.ppf(false_rate)
        
        log.write("d' Target:Foil, {0:.2f}".format(dpTF))
        log.write("d' Target:Lure, {0:.2f}".format(dpTL))
        log.write("d' Lure:Foil, {0:.2f}".format(dpLF))
    else:
        log.write('\nThree-choice test metrics\n')
        sim_lure_rate = TLF_response_matrix[1,1] / TLF_trials[1]
        sim_foil_rate = TLF_response_matrix[1,2] / TLF_trials[2]
        log.write('LDI,{0:.2f}'.format(sim_lure_rate - sim_foil_rate))
    log.flush()
    return 0
 
    
    
    
# ------------------------------------------------------------------------    
# Main routine
params = get_parameters()
print(params)
# Set our random seed
if params['Randomization'] == -1:
    seed = params['ID']
elif params['Randomization']==0:
    seed = None
else:
    seed = params['Randomization']
np.random.seed(seed)

# Get my log file going in append mode
log = open('MST_{0}.txt'.format(params['ID']),"a+")
log.write('MST Task\nStarted at {0}\n'.format(str(datetime.now())))
log.write('ID: {0}\n'.format(params['ID']))
log.write('Duration: {0}\n'.format(params['Duration']))
log.write('ISI: {0}\n'.format(params['ISI']))
log.write('Set: {0}\n'.format(params['Set']))
log.write('Lag set: {0}\n'.format(params['LagSet']))
log.write('Order: {0}\n'.format(params['Order']))
log.write('Respkeys: {0} {1} {2}\n'.format(params['Resp1Keys'],params['Resp1Keys'],params['Resp1Keys']))
log.write('Self-paced: {0}\n'.format(params['SelfPaced']))
log.write('Two-choice: {0}\n'.format(params['TwoChoice']))
log.write('Rnd-mode: {0} with seed {1}\n'.format(params['Randomization'],seed))
log.write('Raw params: {0}'.format(params))
log.write('\n\n')
log.flush()


# Load up the bin file and check the stimulus directory.  Note, the set_bins
# is such that 001a/b.jpg will be first, 002a/b.jpg will be second, etc. 
# So, row = stimulus filename number      
set_bins = np.array(check_files(params['Set']))

# Figure out which stimuli will be shown in which conditions and order them
(repeat_list, lure_list, foil_list) = setup_list_permuted(set_bins)

# Load up the order file and decode it, creating all the needed vectors
(type_code,ideal_resp,lag,fnames)=load_and_decode_order(repeat_list,
        lure_list,foil_list,lag_set=params['LagSet'],
        order=params['Order'], stim_set=params['Set'])



win = visual.Window([800, 800], monitor='testMonitor',color='white')

show_task(params,fnames,type_code,lag,set_bins)
    
win.close()  
log.close()
core.quit()
