# -*- coding: utf-8 -*-
"""
Created on Sat Dec 11 21:52:01 2021

@author: Nicholas Kiriazis
"""
#%% Imports
import pandas as pd
import pathlib
import re
from collections import Counter
import math
import matplotlib.pyplot as plt
import numpy as np
import os.path as osp

parent_dir = pathlib.Path(__file__).parent.resolve()

#%%
data_path = osp.join(parent_dir, '..', 'data', 'tweets3_excel.xlsx') # must replace filename accordingly
stopwords_path = osp.join(parent_dir, '..', 'data', 'stopwords.txt')

#%% Load the data
data_df = pd.read_excel(data_path)
with open(stopwords_path) as f:
        stopwords = f.read().split()

#%% Cleaning dataframe
#data_df.drop(columns=["Column12"], inplace=True)
data_df.rename(columns={"Column1":"TIME", "Column2":"PLACE", "Column3":"TWEET", "Column4":"CATEGORY", "Column5":"SENTIMENT"}, 
                inplace=True)
data_df["SENTIMENT"] = data_df["SENTIMENT"].str.upper()

#%% Clean
clean_df = data_df.loc[data_df["CATEGORY"].isin([1,2,3,4,5])]
clean_df["TWEET"] = clean_df["TWEET"].str.replace('[^0-9a-zA-Z]+', " ", regex=True)
clean_df["TWEET"] = clean_df["TWEET"].str.lower()
clean_df.reset_index(drop=True, inplace=True)

#%% Sentiment breakdown by category
def stacked_bar_plot(full_data): 
    categories = np.sort(full_data["CATEGORY"].unique())
    neg_l = []
    neu_l = []
    pos_l = []
    
    for cat in categories:
        curr_df = full_data.loc[full_data["CATEGORY"]==cat]
        
        neg_l.append(curr_df.loc[curr_df["SENTIMENT"]=="B"].shape[0])
        neu_l.append(curr_df.loc[curr_df["SENTIMENT"]=="N"].shape[0])
        pos_l.append(curr_df.loc[curr_df["SENTIMENT"]=="G"].shape[0])
        
    _, ax = plt.subplots()
    ax.bar(categories, neg_l, label="Negative", color="r")
    ax.bar(categories, neu_l, label="Neutral", bottom=neg_l, color="yellow")
    ax.bar(categories, pos_l, label="Positive", bottom=np.array(neu_l)+np.array(neg_l), color="green")
    ax.set_xlabel("Category")
    ax.set_ylabel("Counts")
    ax.set_title("Sentiment Breakdown by Category")
    ax.legend()
    plt.show()

stacked_bar_plot(clean_df)

#%% Frequency analysis
def get_word_count_dic(series):
    raw_str = series.str.cat(sep=" ").lower()
    clean_str = re.sub('[^0-9a-zA-Z]+', " ", raw_str)
    clean_list = clean_str.split()
    clean_list = [word for word in clean_list if word not in stopwords and not word.isnumeric()]
    count_dic = dict(Counter(clean_list))

    return count_dic

def tf(w, count_dic):    
    if w in count_dic.keys():
        return count_dic[w]
    else:
        return 0

def idf(w, dic_of_count_dics):
    categories = dic_of_count_dics.keys()    
    use_count = 0
    for cat in categories:        
        cat_dic = dic_of_count_dics[cat]
        if w in cat_dic.keys():
            use_count +=1
    return math.log(len(categories)/use_count)

def tf_idf(full_data, selector="CATEGORY", threshold=2):    
    full_word_counts = get_word_count_dic(full_data["TWEET"])
    categories = full_data[selector].unique()
    dic_of_wc_dics = {}
    all_words = []
    
    for cat in categories:
        curr_series = full_data.loc[full_data[selector]==cat]["TWEET"]
        curr_counts = get_word_count_dic(curr_series)
        words_to_drop = []
        
        for word in curr_counts.keys():
            if full_word_counts[word] < threshold:
                words_to_drop.append(word)
        for word in words_to_drop:
            curr_counts.pop(word)
        
        all_words = all_words + list(curr_counts.keys())
        dic_of_wc_dics[cat] = curr_counts
    
    all_words = list(set(all_words))
    tf_idf_dic_dic = {}
    
    for cat in categories:    
        curr_count = dic_of_wc_dics[cat]
        curr_tf_idf_dic = {}
        for w in all_words:
            tfidf = tf(w, curr_count) * idf(w, dic_of_wc_dics)
            curr_tf_idf_dic[w] = tfidf
        tf_idf_dic_dic[cat] = curr_tf_idf_dic

    return tf_idf_dic_dic

#%% Tweet length
def get_tweet_len(tweet):
    words = tweet.split()
    return len(words)

clean_df["TWEET_LENGTH"] = clean_df["TWEET"].apply(get_tweet_len)

#%%
full_tfidf = tf_idf(clean_df, threshold=5)

#%% Top words by tfidf for each category
top_words = []
for i in range(1,6):
    cat_i_words = full_tfidf[float(i)]
    top_words.append(sorted(cat_i_words, key=cat_i_words.get, reverse=True)[:10])
print(top_words)

#%% Verify if tweet mentions top word (i.e. is "on-topic") or not ("off-topic")
def mentions_keyword(tweet, kw_list):
    tweet_words = set(tweet.split())
    kw_set = set(kw_list)    
    return (len(tweet_words & kw_set) != 0)

def keywords_full_df(full_df, list_list_kw):
    output_df = full_df.copy()
    output_df["KEYWORD"] = False
    categories = np.sort(full_df["CATEGORY"].unique())
    
    for c in categories:
        c_df = full_df.loc[full_df["CATEGORY"]==c]
        kw_bool_vector = c_df["TWEET"].apply(lambda t: mentions_keyword(t, list_list_kw[int(c)-1])).to_numpy()
        output_df.loc[c_df.index, "KEYWORD"] = kw_bool_vector
   
    return output_df

final_df = keywords_full_df(clean_df, top_words)

#%% View top ten words, their scores and mean+var of scores for a category
cat = 5

temp_l = []
for w in top_words[cat-1]:
    w_tfidf = full_tfidf[cat][w]
    print(w +" (" + str(round(w_tfidf, 2)) + ")" )
    temp_l.append(w_tfidf)

print(round(np.array(temp_l).mean(), 2))
print(round(np.array(temp_l).var(), 2))

#%% Sentiment breakdown by category
def extra_stacked_bp(full_data, scalefactor=1):
    categories = np.sort(full_data["CATEGORY"].unique())
    neg_on = []
    neg_off = []
    neu_on = []
    neu_off = []
    pos_on = []
    pos_off = []
    
    for cat in categories:
        curr_df = full_data.loc[full_data["CATEGORY"]==cat]
        
        neg_on.append(int(curr_df.loc[curr_df["SENTIMENT"]=="B"]["KEYWORD"].sum()*scalefactor))
        neg_off.append(int((~(curr_df.loc[curr_df["SENTIMENT"]=="B"]["KEYWORD"])).sum()*scalefactor))
        
        neu_on.append(int(curr_df.loc[curr_df["SENTIMENT"]=="N"]["KEYWORD"].sum()*scalefactor))
        neu_off.append(int((~(curr_df.loc[curr_df["SENTIMENT"]=="N"]["KEYWORD"])).sum()*scalefactor))
        
        pos_on.append(int(curr_df.loc[curr_df["SENTIMENT"]=="G"]["KEYWORD"].sum()*scalefactor))
        pos_off.append(int((~(curr_df.loc[curr_df["SENTIMENT"]=="G"]["KEYWORD"])).sum()*scalefactor))
    
    _, ax = plt.subplots()
    
    neg_total = np.array(neg_on) + np.array(neg_off)
    neu_total = np.array(neu_on) + np.array(neu_off)

    ax.bar(categories, neg_on, label="Negative - On Topic", color="#ff3838")
    ax.bar(categories, neg_off, label="Negative - Off Topic", color="#f59595", bottom=neg_on)
    
    ax.bar(categories, neu_on, label="Neutral - On Topic", color="#007bff", bottom=neg_total)
    ax.bar(categories, neu_off, label="Neutral - Off Topic", color="#95c3f5", bottom=neg_total+np.array(neu_on))
    
    ax.bar(categories, pos_on, label="Positive - On Topic", color="#18ed4a", bottom=neg_total+neu_total)
    ax.bar(categories, pos_off, label="Positive - Off Topic", color="#a2f2b5", bottom=neg_total+neu_total+np.array(pos_on))

    ax.set_xlabel("Category")
    ax.set_ylabel("Counts")
    ax.set_title("Sentiment Breakdown by Category")
    
    ax.legend(bbox_to_anchor=(-0.15,-0.15), loc="upper left", ncol=3)
    
    plt.show()

extra_stacked_bp(final_df)

#%% Tweet length by category and sentiment
sent_cat_grouped = final_df.groupby(["CATEGORY", "SENTIMENT"])["TWEET_LENGTH", "KEYWORD"].mean().reset_index()
z = sent_cat_grouped.pivot(index="SENTIMENT", columns="CATEGORY", values="TWEET_LENGTH")

def comparison_bp(length_df):
    _, ax = plt.subplots()
    pos = length_df.loc["G",:].to_numpy()
    neu = length_df.loc["N",:].to_numpy()
    neg = length_df.loc["B",:].to_numpy()
    
    indices = np.array([int(i) for i in length_df.columns])
    width = 0.3
    
    ax.bar(indices-width, neg, width=width, color="#ff3838", label="Negative")
    ax.bar(indices, neu, width=width, color="#007bff", label="Neutral")
    ax.bar(indices+width, pos, width=width, color="#18ed4a", label="Positive")
    
    ax.set_xlabel("Category")
    ax.set_ylabel("Length")
    ax.set_title("Tweet Length by Category and Sentiment")
    
    ax.legend(bbox_to_anchor=(0.08,-0.15), loc="upper left", ncol=3)
    
    plt.show()
    
comparison_bp(z)
# %%
