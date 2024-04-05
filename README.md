[![PyPI](https://img.shields.io/pypi/v/memento-ml)](https://pypi.org/project/memento-ml/)
![Python versions](https://img.shields.io/pypi/pyversions/memento-ml)
[![DOI](https://zenodo.org/badge/608197208.svg)](https://zenodo.org/doi/10.5281/zenodo.10929405)


# MEMENTO

`MEMENTO` is a Python library for running computationally expensive experiments.

Running complex sets of machine learning experiments is challenging and time-consuming due to the lack of a unified framework.
This leaves researchers forced to spend time implementing necessary features such as parallelization, caching, and checkpointing themselves instead of focussing on their project.
To simplify the process, we introduce `MEMENTO`, a Python package that is designed to aid researchers and data scientists in the efficient management and execution of computationally intensive experiments.
`MEMENTO` has the capacity to streamline any experimental pipeline by providing a straightforward configuration matrix and the ability to concurrently run experiments across multiple threads.

If you need to run a large number of time-consuming experiments `MEMENTO` can help:

- Structure your configuration
- Parallelize experiments across CPUs
- Save and restore results
- Checkpoint in-progress experiments
- Send notifications when experiments fail or finish

[![Demo video](https://img.youtube.com/vi/GEtdCl1ZUWc/0.jpg)](http://www.youtube.com/watch?v=GEtdCl1ZUWc)

## Getting Started

`MEMENTO` is officially available on PyPl. To install the package:

### Install

```bash
pip install memento-ml
```

### The Configuration Matrix

The core of `MEMENTO` is a configuration `matrix` that describes the list of experiments you
want `MEMENTO` to run. This must contain a key `parameters` which is itself a dict, this describes
each paramter you want to vary for your experiments and their values.

As an example let's say you wanted to test a few simple linear classifiers on a number of
image recognition datasets. You might write something like this:

> Don't worry if you're not working on machine learning, this is just an example.

```python
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
```

`MEMENTO` would then generate 12 configurations by taking the _cartesian product_ of the
parameters.

Frequently you might also want to set some global configuration values, such as a regularization
parameter or potentially even change your preprocessing pipeline. In this case `MEMENTO` also
accepts a "settings" key. These settings apply to all experiments and can be accessed from the
configuration list as well as individual configurations.

```python
matrix = {
  "parameters": ...,
  "settings": {
    "regularization": 1e-1,
    "preprocessing": make_preprocessing_pipeline()
  }
}
```

You can also exclude specific parameter configurations. Returning to our machine learning
example, if you know SVCs perform poorly on cifar10 you might decide to skip that
experiment entirely. This is done with the "exclude" key:

```python
matrix = {
  "parameters": ...,
  "exclude": [
    {"model": sklearn.svm.SVC, "dataset": "cifar10"}
  ]
}
```

### Running an experiment

Along with a configuration matrix you need some code to run your experiments. This can be any
`Callable` such as a function, lambda, class, or class method.

```python
from memento import Memento, Config, Context

def experiment(context: Context, config: Config):
  classifier = config.model()
  dataset = fetch_dataset(config.dataset)

  classifier.fit(*dataset)

  return classifier

Memento(experiment).run(matrix)
```

You can also perform a dry run to check you've gotten the matrix correct.

```python
Memento(experiment).run(matrix, dry_run=True)
```

```python
Running configurations:
  {'model': sklearn.svm.SVC, 'dataset': 'imagenet'}
  {'model': sklearn.svm.SVC, 'dataset': 'mnist'}
  {'model': sklearn.svm.SVC, 'dataset': 'cifar10'}
  {'model': sklearn.svm.SVC, 'dataset': 'quickdraw'}
  {'model': sklearn.linear_model.Perceptron, 'dataset': 'imagenet'}
  ...
Exiting due to dry run
```

## Code demo

- Code demo can be found [here](demo).
- `MEMENTO` does not depend on any ML packages, e.g., `scikit-learn`. The `scikit-learn` and `jupyterlab` packages are required to run the demo (`./demo/*`).

```bash
pip install memento-ml scikit-learn jupyterlab
```

## Cite

If you find `MEMENTO` useful and use it in your research, please cite

> Memento: Facilitating Effortless, Efficient, and Reliable ML Experiments - 
> Z Pullar-Strecker, X Chang, L Brydon, I Ziogas, K Dost, J Wicker -
> Joint European Conference on Machine Learning and Knowledge Discovery in Databases, 2023 - Springer -
> https://link.springer.com/chapter/10.1007/978-3-031-43430-3_21

## Roadmap

- Finish HPC support
- Improve result serialisation
- Improve customization for notification

## Contributors

- [Zac Pullar-Strecker](https://github.com/zacps)
- [Feras Albaroudi](https://github.com/NeedsSoySauce)
- [Liam Scott-Russell](https://github.com/Liam-Scott-Russell)
- [Joshua de Wet](https://github.com/Dewera)
- [Nipun Jasti](https://github.com/watefeenex)
- [James Lamberton](https://github.com/JamesLamberton)
- [Xinglong (Luke) Chang](https://github.com/changx03)
- [Liam Brydon](https://github.com/MyCreativityOutlet)
- [Ioannis Ziogas](izio995@aucklanduni.ac.nz)
- [Katharina Dost](katharina.dost@auckland.ac.nz)
- [Joerg Wicker](https://github.com/joergwicker)

## License

MEMENTO is licensed under the [3-Clause BSD License](https://opensource.org/licenses/BSD-3-Clause) license.
