import functools
from pprint import pprint

from sklearn import datasets
from sklearn.ensemble import (
    AdaBoostClassifier,
    BaggingClassifier,
    RandomForestClassifier,
)
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from memento import Memento, Config, Context


matrix = {
    "parameters": {
        "classifier": [
            AdaBoostClassifier,
            BaggingClassifier,
            DecisionTreeClassifier,
            RandomForestClassifier,
            SVC,
        ],
        "dataset": [
            functools.partial(datasets.load_iris, return_X_y=True),
            functools.partial(datasets.load_digits, return_X_y=True),
            functools.partial(datasets.load_wine, return_X_y=True),
            functools.partial(datasets.load_breast_cancer, return_X_y=True),
        ],
    }
}


def experiment(context: Context, config: Config):
    classifier = config.classifier()
    x, y = config.dataset()

    if context.checkpoint_exist():
        scores = context.restore()
    else:
        scores = cross_val_score(classifier, x, y, cv=10)
        context.checkpoint(scores)

    return scores.mean()


if __name__ == "__main__":
    results = Memento(experiment).run(matrix)
    pprint([result.inner for result in results])
