import numpy as np
from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score
import django

def ridge_regress(target, U, V, fix_u, lam=0.8, lr=0.03, max_iter=1000, debug=False):
    for iter in range(max_iter):
        user, item, rating = target[np.random.choice(len(target))]
        #old_delta = np.abs(np.dot(U[user], V[item].T) - rating)
        if fix_u:
            V[item] = V[item] - lr * ((np.dot(U[user], V[item].T) - rating) * U[user] + lam * V[item])
        else:
            U[user] = U[user] - lr * ((np.dot(U[user], V[item].T) - rating) * V[item] + lam * U[user])
        #if np.abs(np.dot(U[user], V[item].T) - rating) > old_delta:
        #    print(np.abs(np.dot(U[user], V[item].T) - rating) - old_delta)
    if debug:
        deltas = np.array([(np.dot(U[user], V[item].T) - rating) for user, item, rating in target])
        print("RMSE:", np.sqrt((deltas ** 2).mean()))

def recommender(input_ratings, num_users, num_subjects, num_features, num_alternations=1000, verbose=False):
    U = np.zeros((num_users, num_features)) #.random.uniform(-1.0, 1.0, (num_users, num_features))
    V = np.random.uniform(-2.0, 2.0, (num_subjects, num_features))

    for i in range(num_alternations):
        if verbose:
            print("Alternation {}".format(i))
        # Fix V first, ridge regression on U
        old_u = np.copy(U)
        old_v = np.copy(V)
        ridge_regress(input_ratings, U, V, False, max_iter=100, debug=False)
        # Fix U
        ridge_regress(input_ratings, U, V, True, max_iter=100, debug=False)
        #print((old_u - U).mean(), (old_v - V).mean())
    return U, V

def test_recommender():
    num_users = 10
    num_subjects = 5
    subjects = ["6.006", "2.009", "6.046", "21M.284", "6.854"]
    num_alternations = 1000
    max_rating = 5
    # User, subject, rating (-5 to 5)
    user_ratings = [
        [(1, 4),
         (3, -3)],
        [(0, 5),
         (2, 5)],
        [(3, 4),
         (4, -2)],
        [(0, 2),
         (1, 4)],
        [(2, 4)],
        [(3, -1),
         (4, -4)],
        [(0, 5),
         (1, 5)],
        [(1, 4),
         (2, -3)],
        [(1, 2)],
        [(0, 3),
         (2, -3)]
    ]
    input_ratings = []
    for i, user in enumerate(user_ratings):
        max_value = max(np.abs(rating) for item, rating in user)
        for item, rating in user:
            input_ratings.append((i, item, rating / max_value * max_rating))
    print(input_ratings)

    best_rmse = 9999999
    best_u = None
    best_v = None
    for num_features in range(1, 20, 3):
        print(num_features, "...")
        U, V = recommender(input_ratings, num_users, num_subjects, num_features, verbose=False)
        deltas = np.array([(np.dot(U[user], V[item].T) - rating) for user, item, rating in input_ratings])
        rmse = np.sqrt((deltas ** 2).mean())
        print("RMSE:", rmse)
        if rmse < best_rmse:
            best_rmse = rmse
            best_u = U
            best_v = V

    Y = np.dot(best_u, best_v.T)
    print(Y)
    for (user, item, rating) in input_ratings:
        print(user, subjects[item], rating, Y[user,item])
    for user in range(num_users):
        print(user, subjects[Y[user].argmax()])

### Getting data from SQlite
if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
    django.setup()
    from recommend.models import Rating
    print(Rating.objects.all())
