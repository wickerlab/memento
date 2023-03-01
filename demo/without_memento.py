from sklearn import datasets
from sklearn.ensemble import (
    AdaBoostClassifier,
    BaggingClassifier,
    RandomForestClassifier,
)
from sklearn.model_selection import cross_val_score
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

# Load datasets

iris_x, iris_y = datasets.load_iris(return_X_y=True)
digits_x, digits_y = datasets.load_digits(return_X_y=True)
wine_x, wine_y = datasets.load_wine(return_X_y=True)
wine_y_broken = wine_y[:-1]
breast_x, breast_y = datasets.load_breast_cancer(return_X_y=True)


def run_classifiers(x, y):
    # Initialise classifiers

    ada_boost_classifier = AdaBoostClassifier()
    bagging_classifier = BaggingClassifier()
    decision_tree_classifier = DecisionTreeClassifier()
    random_forest_classifier = RandomForestClassifier()
    simple_vector_machine_classifier = SVC()

    # Cross validate each classifier 10 times

    ada_boost_scores = cross_val_score(ada_boost_classifier, x, y, cv=10)
    bagging_scores = cross_val_score(bagging_classifier, x, y, cv=10)
    decision_tree_scores = cross_val_score(decision_tree_classifier, x, y, cv=10)
    random_forest_scores = cross_val_score(random_forest_classifier, x, y, cv=10)
    simple_vector_machine_scores = cross_val_score(
        simple_vector_machine_classifier, x, y, cv=10
    )

    # Output mean accuracy for each classifier

    print(f"Mean accuracy of ADA Boost classifier: {ada_boost_scores.mean()}")
    print(f"Mean accuracy of Bagging classifier: {bagging_scores.mean()}")
    print(f"Mean accuracy of Decision Tree classifier: {decision_tree_scores.mean()}")
    print(f"Mean accuracy of Random Forest classifier: {random_forest_scores.mean()}")
    print(
        f"Mean accuracy of Simple Vector Machine classifier: {simple_vector_machine_scores.mean()}"
    )
    print()


import time

t0 = time.time()


print("Iris dataset\n")
run_classifiers(iris_x, iris_y)

print("Digits dataset\n")
run_classifiers(digits_x, digits_y)

print("Wine dataset\n")
# run_classifiers(wine_x, wine_y_broken)
run_classifiers(wine_x, wine_y)

print("Breast cancer dataset\n")
run_classifiers(breast_x, breast_y)

t1 = time.time()

total = t1 - t0
print(total)
