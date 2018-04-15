from models import GTLibraryGridWarehouse
import utils
from tsp import held_karp as tsp_help_karp
import numpy as np
import json
import logging
import os

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.configure_logger(logger)


PICK_PATH_FILE_FORMAT_VERSION = '1.1'


def generate_pick_path_as_dict(gt_library_warehouse, books_per_pick_path, source):  # type: (GTLibraryGridWarehouse, int, (int, int)) -> dict

    logger.debug('Choosing %d books at random.' % books_per_pick_path)
    unordered_books = np.random.choice(
        a=gt_library_warehouse.books,
        size=books_per_pick_path,
        replace=False,
    )

    unordered_books_locations = gt_library_warehouse.get_books_locations(unordered_books)

    logger.debug('Getting sub-graph on chosen book locations and source for TSP.')
    # If two books are on the same column, this method will consider them the same cell,
    # This is why we'll need reintroduce_duplicate_column_locations later
    G_subgraph = utils.get_subgraph_on_book_locations(gt_library_warehouse, unordered_books_locations, source)

    logger.debug('Solving TSP for selected books.')
    optimal_pick_path, optimal_cost = tsp_help_karp.solver(G_subgraph, source)

    logger.debug('Patching up solution.')
    ordered_books, ordered_locations = utils.reintroduce_duplicate_column_locations(
        zip(unordered_books, unordered_books_locations), source, optimal_pick_path)

    # The optimal pick path has two more source locations (source, ..., source)
    assert len(unordered_books) == len(ordered_books) - 2 == len(ordered_locations) - 2

    logger.debug('Computing cell-by-cell pick path in library based on TSP solution.')
    optimal_pick_path_in_library = utils.get_pick_path_in_library(gt_library_warehouse, ordered_locations, source)

    logger.debug('Verifying solution has right format and cost.')
    utils.assert_library_pick_path_is_proper(optimal_pick_path_in_library, ordered_locations, source)
    utils.assert_library_pick_path_has_cost(optimal_pick_path_in_library, optimal_cost, len(ordered_books[1:-1]))

    logger.debug('Packaging solution in dictionary.')
    return utils.get_pick_path_as_dict(
        unordered_books, unordered_books_locations, ordered_books, ordered_locations, optimal_pick_path_in_library)


def get_pick_paths(number_of_training_pick_paths, number_of_testing_pick_paths, books_per_pick_path, source):
    # East-side of library is top of array
    gt_library_warehouse = utils.get_warehouse('warehouse.json')

    pick_paths = []

    for i in range(number_of_training_pick_paths + number_of_testing_pick_paths):
        logger.info("Processing path #%s" % (i + 1,))

        pick_path_as_dict = generate_pick_path_as_dict(gt_library_warehouse, books_per_pick_path, source)

        pick_paths.append({
            'pathId': i + 1,
            'pathType': 'training' if i < number_of_training_pick_paths else 'testing',
            'pickPathInformation': pick_path_as_dict
        })

        logger.info("Completed path #%s" % (i + 1,))

    return pick_paths


if __name__ == '__main__':
    np.random.seed(1)

    pick_paths = get_pick_paths(
        number_of_training_pick_paths=20,
        number_of_testing_pick_paths=20,
        books_per_pick_path=10,
        source=(0, 0),
    )

    with open('pick-paths.json', mode='w+') as f:
        json.dump(
            obj={
                'version': PICK_PATH_FILE_FORMAT_VERSION,
                'pickPaths': pick_paths
            },
            fp=f,
            indent=4,
        )
