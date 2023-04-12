from sklearn.datasets import load_digits, load_wine
from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import SVC
import pandas as pd
import logging

from memento import Config, Context, Memento

logging.basicConfig(level=logging.INFO)


def experiment(context: Context, config: Config):
    data = config.dataset()
    model = config.classifier()

    cv = config.settings["n_fold"]

    pipeline = make_pipeline(config.preprocessing, model)
    results = cross_val_score(pipeline, data.data, data.target, cv=cv)
    context.checkpoint(results)
    return results.mean() * 100


def resultsToTable(results):
    res = [[round(r.inner, 2), r.config.dataset.__name__, r.config.preprocessing.__class__.__name__,
            r.config.classifier.__name__] for r in results]
    return pd.DataFrame(res, columns=['Accuracy', 'Dataset', 'Preprocessing', 'Classifier'])


def main():
    matrix = {
        "parameters": {
            "dataset": [load_digits, load_wine],
            "preprocessing": [MinMaxScaler(), StandardScaler()],
            "classifier": [AdaBoostClassifier, RandomForestClassifier, SVC],
        },
        "settings": {
            "n_fold": 20,
        },
        "exclude": [
            {"dataset": load_digits, "classifier": SVC},
        ],
    }
    Memento(experiment).run(matrix, dry_run=True)
    results = Memento(experiment).run(matrix)
    return results


if __name__ == "__main__":
    print(resultsToTable(main()))
