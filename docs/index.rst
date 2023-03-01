.. MEMENTO documentation master file, created by
   sphinx-quickstart on Mon Mar 22 17:48:51 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to MEMENTO's documentation!
===================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Getting Started
===============

The Configuration Matrix
------------------------

The core of MEMENTO is a configuration ``matrix`` that describes the list of experiments you
want MEMENTO to run. This must contain a key ``parameters`` which is itself a dict, this describes
each paramter you want to vary for your experiments and their values.

As an example let's say you wanted to test a few simple linear classifiers on a number of
image recognition datasets. You might write something like this:

.. note::
   Don't worry if you're not working on machine learning, this is just an example.

::

   matrix = {
      "parameters": {
            "model": [
               sklearn.svm.SVC,
               sklearn.linear_model.Perceptron,
               sklearn.linear_model.LogisticRegression
            ],
            "dataset": ["imagenet", "mnist", "cifar10", "quickdraw"]
      }
   }

MEMENTO would then generate 12 configurations by taking the *cartesian product* of the
parameters.

Frequently you might also want to set some global configuration values, such as a regularization
parameter or potentially even change your preprocessing pipeline. In this case MEMENTO also
accepts a "settings" key. These settings apply to all experiments and can be accessed from the
configuration list as well as individual configurations.

::

   matrix = {
      "parameters": ...,
      "settings": {
            "regularization": 1e-1,
            "preprocessing": make_preprocessing_pipeline()
      }
   }

You can also exclude specific parameter configurations. Returning to our machine learning
example, if you know SVCs perform poorly on cifar10 you might decide to skip that
experiment entirely. This is done with the "exclude" key:

::

   matrix = {
      "parameters": ...,
      "exclude": [
            {"model": sklearn.svm.SVC, "dataset": "cifar10"}
      ]
   }

Running an experiment
---------------------

Along with a configuration matrix you need some code to run your experiments. This can be any
``Callable`` such as a function, lambda, class, or class method.

::

   from memento import Memento, Config, Context

   def experiment(context: Context, config: Config):
      classifier = config.model()
      dataset = fetch_dataset(config.dataset)

      classifier.fit(*dataset)

      return classifier

   Memento(experiment).run(matrix)

::

   <memento.configurations.Configurations object at 0x0000012FE7D20AF0>

You can also perform a dry run to check you've gotten the matrix correct.

::

   Memento(experiment).run(matrix, dry_run=True)

::

   Running configurations:
      {'model': sklearn.svm.SVC, 'dataset': 'imagenet'}
      {'model': sklearn.svm.SVC, 'dataset': 'mnist'}
      {'model': sklearn.svm.SVC, 'dataset': 'cifar10'}
      {'model': sklearn.svm.SVC, 'dataset': 'quickdraw'}
      {'model': sklearn.linear_model.Perceptron, 'dataset': 'imagenet'}
      ...
   Exiting due to dry run
