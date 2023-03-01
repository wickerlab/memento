from memento.configurations import generate_configurations


def test_configurations_no_exclude():
    matrix = {
        "parameters": {"param1": [1, 2], "param2": [3, 4]},
    }

    configs = generate_configurations(matrix)
    expected = [
        {"param1": 1, "param2": 3},
        {"param1": 1, "param2": 4},
        {"param1": 2, "param2": 3},
        {"param1": 2, "param2": 4},
    ]

    assert len(configs) == len(expected)

    for config, expected in zip(configs, expected):
        assert config.asdict() == expected


def test_configurations():
    matrix = {
        "parameters": {"param1": [1, 2, 3], "param2": [4, 5, 6]},
        "exclude": [{"param1": 3, "param2": 6}],
    }

    configs = generate_configurations(matrix)
    expected = [
        {"param1": 1, "param2": 4},
        {"param1": 1, "param2": 5},
        {"param1": 1, "param2": 6},
        {"param1": 2, "param2": 4},
        {"param1": 2, "param2": 5},
        {"param1": 2, "param2": 6},
        {"param1": 3, "param2": 4},
        {"param1": 3, "param2": 5},
        # Excluded
        # {"param1": 3, "param2": 6},
    ]

    assert len(configs) == len(expected)

    for config, expected in zip(configs, expected):
        assert config.asdict() == expected


def test_configurations_multi_steps():
    matrix = {
        "parameters": {
            "param1": [1, 2, 3],
            "param2": [4, 5, 6],
            "param3": [7, 8],
        },
        "exclude": [{"param1": 3, "param2": 5}],
    }

    configs = generate_configurations(matrix)
    expected = [
        {"param1": 1, "param2": 4, "param3": 7},
        {"param1": 1, "param2": 4, "param3": 8},
        {"param1": 1, "param2": 5, "param3": 7},
        {"param1": 1, "param2": 5, "param3": 8},
        {"param1": 1, "param2": 6, "param3": 7},
        {"param1": 1, "param2": 6, "param3": 8},
        {"param1": 2, "param2": 4, "param3": 7},
        {"param1": 2, "param2": 4, "param3": 8},
        {"param1": 2, "param2": 5, "param3": 7},
        {"param1": 2, "param2": 5, "param3": 8},
        {"param1": 2, "param2": 6, "param3": 7},
        {"param1": 2, "param2": 6, "param3": 8},
        {"param1": 3, "param2": 4, "param3": 7},
        {"param1": 3, "param2": 4, "param3": 8},
        {"param1": 3, "param2": 6, "param3": 7},
        {"param1": 3, "param2": 6, "param3": 8},
        # Excluded
        # {"param1": 3, "param2": 5, "param3": 7},
        # {"param1": 3, "param2": 5, "param3": 8},
    ]

    assert len(configs) == len(expected)

    for config, expected in zip(configs, expected):
        assert config.asdict() == expected


if __name__ == "__main__":
    test_configurations()
