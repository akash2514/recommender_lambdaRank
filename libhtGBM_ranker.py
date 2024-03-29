# -*- coding: utf-8 -*-
"""Untitled31.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1sDw6-WDDy_3PhM9JmNJR7zyzMkkJz7Uk
"""

from sklearn.metrics import f1_score,precision_score,recall_score,accuracy_score

import numpy as np
import pandas as pd
import lightgbm
import time
from sklearn.model_selection import GroupShuffleSplit


df = pd.DataFrame({
    "query_id":[i for i in range(100) for j in range(10)],
    "var1":np.random.random(size=(1000,)),
    "var2":np.random.random(size=(1000,)),
    "var3":np.random.random(size=(1000,)),
    "relevance":list(np.random.permutation([0,0,0,0,0, 0,0,0,1,1]))*100
})

df = pd.DataFrame({
    "query_id":[i for i in range(100) for j in range(10)],
    "var1":list(range(1,6))*200,
    # "var2":np.random.random(size=(1000,)),
    # "var3":np.random.random(size=(1000,)),
    "relevance":list(np.random.permutation([0,0,0,0,0, 0,0,0,1,1]))*100
})

df.to_csv(r'D:\python\datasets\dummy_dataset\test_ltr.csv',index=None)

from sklearn.preprocessing import StandardScaler

sc = StandardScaler()

########################################################################################################

df = pd.read_csv(r'D:\python\datasets\dummy_dataset\test_ltr.csv')
df["var1"] =df["var1"].astype('category')
df["var2"] =df["var2"].astype(int)

df.sort_values(by=['query_id'],ascending=True,inplace=True) # qids_train = 80, ('ndcg@1', 0.2)
gss = GroupShuffleSplit(test_size=.40, n_splits=1, random_state = 7).split(df, groups=df['query_id'])
X_train_inds, X_test_inds = next(gss)
train_data= df.iloc[X_train_inds]
test_data= df.iloc[X_test_inds]
qids_train = train_data.groupby("query_id")["query_id"].count().to_numpy()
X_train = train_data.drop(["query_id", "relevance"], axis=1)
y_train = train_data["relevance"]
qids_validation = test_data.groupby("query_id")["query_id"].count().to_numpy()
X_validation = test_data.drop(["query_id", "relevance"], axis=1)
y_validation = test_data["relevance"]

dic = {}
learning_rate = [0.005,0.01,0.05,0.1]
for k in learning_rate:
    model = lightgbm.LGBMRanker(objective="lambdarank",metric="ndcg",learning_rate=k,n_estimators=1000)
    model.fit(
        X=X_train,
        y=y_train,
        group=qids_train,
        eval_set=[(X_validation, y_validation)],
        eval_group=[qids_validation],
        eval_at=[1,5,10,20],
        verbose=10,
        early_stopping_rounds=200
    )
    dic[k] = model.best_score_['valid_0']['ndcg@1']
print(dic)


#####################################################################################################################################3

# Fine tuning

import optuna  # pip install optuna
from sklearn.metrics import log_loss
from sklearn.model_selection import StratifiedKFold

def objective(trial, X, y):
    param_grid = {
        # "device_type": trial.suggest_categorical("device_type", ['gpu']),
        "n_estimators": trial.suggest_categorical("n_estimators", [1000]),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
        "num_leaves": trial.suggest_int("num_leaves", 20, 3000, step=20),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 200, 10000, step=100),
        "lambda_l1": trial.suggest_int("lambda_l1", 0, 100, step=5),
        "lambda_l2": trial.suggest_int("lambda_l2", 0, 100, step=5),
        "min_gain_to_split": trial.suggest_float("min_gain_to_split", 0, 15),
        "bagging_fraction": trial.suggest_float(
            "bagging_fraction", 0.2, 0.95, step=0.1
        ),
        "bagging_freq": trial.suggest_categorical("bagging_freq", [1]),
        "feature_fraction": trial.suggest_float(
            "feature_fraction", 0.2, 0.95, step=0.1
        ),
    }
    # cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=1121218)
    n_splits = 5
    gss = GroupShuffleSplit(n_splits=n_splits,test_size=.20, random_state=7).split(df, groups=df['query_id'])

    cv_scores = np.empty(5)
    # for idx, (train_idx, test_idx) in enumerate(cv.split(X, y)):
    for n_splits in gss.split(df, groups=df['query_id']):
        X_train_inds, X_test_inds = next(gss)
        train_data = df.iloc[X_train_inds]
        test_data = df.iloc[X_test_inds]

        qids_train = train_data.groupby("query_id")["query_id"].count().to_numpy()
        X_train = train_data.drop(["query_id", "relevance"], axis=1)
        y_train = train_data["relevance"]

        qids_validation = test_data.groupby("query_id")["query_id"].count().to_numpy()
        X_test = test_data.drop(["query_id", "relevance"], axis=1)
        y_test = test_data["relevance"]

        # model = lgbm.LGBMClassifier(objective="binary", **param_grid)
        model = lightgbm.LGBMRanker(objective="lambdarank",metric="ndcg",**param_grid)
        model.fit(
            X=X_train,
            y=y_train,
            group=qids_train,
            eval_set=[(X_test, y_test)],
            eval_group=[qids_validation],
            eval_at=[1, 5, 10, 20],
            verbose=10,
        )



        cv_scores[n_splits] = model.best_score_['valid_0']['ndcg@1']

    return np.mean(cv_scores)

study = optuna.create_study(direction="minimize", study_name="LGBM Classifier")
func = lambda trial: objective(trial, X, y)
study.optimize(func, n_trials=20)
print(f"\tBest value (rmse): {study.best_value:.5f}")
print(f"\tBest params:")
for key, value in study.best_params.items():
    print(f"\t\t{key}: {value}")
