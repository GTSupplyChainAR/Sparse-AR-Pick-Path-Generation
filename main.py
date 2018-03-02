from models import LibraryRow, NAVIGABLE_CELL
import utils
from tsp import held_karp as tsp_help_karp
import numpy as np
import json
import logging
import os

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
_hdlr = logging.StreamHandler()
_formatter = logging.Formatter('%(name)-12s %(levelname)-8s %(asctime)-30s %(message)s')
_hdlr.setFormatter(_formatter)
_hdlr.setLevel(logging.DEBUG)
logger.addHandler(_hdlr)


def generate_pick_path_as_dict(books_repo, gt_library_layout, books_per_pick_path, source):
    unordered_books = np.random.choice(
        a=books_repo.values(),
        size=books_per_pick_path,
        replace=False,
    )

    unordered_books, unordered_books_locations = utils.get_books_locations(unordered_books, gt_library_layout)

    # If two books are on the same column, this method will consider them the same cell,
    # This is why we'll need reintroduce_duplicate_column_locations later
    G_subgraph = utils.get_subgraph_on_book_locations(gt_library_layout, unordered_books_locations, source)

    optimal_pick_path, optimal_cost = tsp_help_karp.solver(G_subgraph, source)

    ordered_books, ordered_locations = utils.reintroduce_duplicate_column_locations(
        zip(unordered_books, unordered_books_locations), source, optimal_pick_path)

    # The optimal pick path has two more source locations (source, ..., source)
    assert len(unordered_books) == len(ordered_books) - 2 == len(ordered_locations) - 2

    optimal_pick_path_in_library = utils.get_pick_path_in_library(gt_library_layout, ordered_books, ordered_locations,
                                                                  source)

    utils.assert_library_pick_path_is_proper(optimal_pick_path_in_library, ordered_locations, source)
    utils.assert_library_pick_path_has_cost(optimal_pick_path_in_library, optimal_cost, len(ordered_books[1:-1]))

    return utils.get_pick_path_as_dict(unordered_books, unordered_books_locations, ordered_books, ordered_locations,
                                       optimal_pick_path_in_library)


def get_pick_paths(number_of_training_pick_paths, number_of_testing_pick_paths, books_per_pick_path, source):
    books_repo = utils.get_books_repository('books.json')

    # East-side of library is top of array
    gt_library_layout = [
        [NAVIGABLE_CELL] * 8,
        [NAVIGABLE_CELL] + LibraryRow('A').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],
        [NAVIGABLE_CELL] + LibraryRow('B').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],

        [NAVIGABLE_CELL] * 8,
        [NAVIGABLE_CELL] + LibraryRow('C').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],
        [NAVIGABLE_CELL] + LibraryRow('D').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],

        [NAVIGABLE_CELL] * 8,
        [NAVIGABLE_CELL] + LibraryRow('E').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],
        [NAVIGABLE_CELL] + LibraryRow('F').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],

        [NAVIGABLE_CELL] * 8,
        [NAVIGABLE_CELL] + LibraryRow('G').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],
        [NAVIGABLE_CELL] + LibraryRow('H').get_shelving_columns(books_repo) + [NAVIGABLE_CELL],

        [NAVIGABLE_CELL] * 8,
    ]

    pick_paths = []

    for i in range(number_of_training_pick_paths + number_of_testing_pick_paths):
        logger.info("Processing path #%s" % (i + 1,))

        pick_path_as_dict = generate_pick_path_as_dict(books_repo, gt_library_layout, books_per_pick_path, source)

        pick_paths.append({
            'pathId': i + 1,
            'pathType': 'training' if i < number_of_training_pick_paths else 'testing',
            'pickPathInformation': pick_path_as_dict
        })

        logger.info("Completed path #%s" % (i + 1,))

    return pick_paths


if __name__ == '__main__':
    # np.random.seed(42)

    pick_paths = get_pick_paths(
        number_of_training_pick_paths=10,
        number_of_testing_pick_paths=10,
        books_per_pick_path=10,
        source=(0, 0)
    )

    with open('output.json', mode='w+') as f:
        json.dump(pick_paths, f, indent=4)