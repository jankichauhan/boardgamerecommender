import pandas as pd
import pickle
import numpy as np
from fastai.collab import *
import os.path
from sklearn.neighbors import NearestNeighbors

class Collabrative:
    MODEL_NAME = 'Collabrative'
    COUNT_LIMIT = 2000

    def __init__(self):
        print("in init")


    def transform(self):
        print(" in transform")

        self.user_ratings = pd.read_csv('../data/bgg_user_ratings.csv', index_col=0)

        games_by_users = self.user_ratings.groupby('name')['rating'].agg(['mean', 'count']).sort_values('mean', ascending=False)
        games_by_users['rank'] = games_by_users.reset_index().index + 1

        data_user_rating = CollabDataBunch.from_df(self.user_ratings, user_name='user', item_name='name', rating_name='rating', bs=100000,
                                       seed=42)
        learner = collab_learner(data_user_rating, n_factors=50, y_range=(2., 10))
        learner.fit_one_cycle(3, 1e-2, wd=0.15)

        top_games = games_by_users[games_by_users['count'] > self.COUNT_LIMIT].sort_values('mean', ascending=False).reset_index()
        number_of_games = len(top_games)

        # mean_ratings = self.user_ratings.groupby('name')['rating'].mean().round(2)
        game_weights = learner.weight(top_games['name'], is_item=True)
        game_bias = learner.bias(top_games['name'], is_item=True)
        npweights = game_weights.numpy()
        top_games['model_score'] = game_bias.numpy()
        top_games['weights_sum'] = np.sum(np.abs(npweights), axis=1)

        top_games.index.name = 'id'
        top_games.to_csv("../data/top_games.csv")

        weights_df = pd.DataFrame(npweights)
        weights_df.index.name = 'id'
        weights_df.to_csv("../data/weights.csv")

        nn = NearestNeighbors(n_neighbors=number_of_games)
        fitnn = nn.fit(npweights)
        pickle.dump(fitnn, open("../static/model.pkl", "wb"))

    def get_recommendations(self, game):
        print("in recommedations")

        if os.path.isfile('../static/model.pkl') == False:
            self.transform()

        top_games_df = pd.read_csv("../data/top_games.csv", index_col='id')
        weights_df = pd.read_csv("../data/weights.csv", index_col='id').to_numpy()

        print(" ", top_games_df.info())
        print(" ", type(weights_df))

        fitnn_model = pickle.load(open('../static/model.pkl', 'rb'))
        res = top_games_df[top_games_df['name'] == game]
        if len(res) == 1:
            distances, indices = fitnn_model.kneighbors([weights_df[res.index[0]]])
        else:
            print(res.head())
        print(top_games_df.iloc[indices[0][:10]].sort_values('model_score', ascending=False))

        recommendation_df = top_games_df.iloc[indices[0][:10]].sort_values('model_score', ascending=False)

        return recommendation_df