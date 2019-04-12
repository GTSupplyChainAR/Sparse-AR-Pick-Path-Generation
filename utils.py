import json
import os
import logging
import networkx as nx
import itertools
from constants import NAVIGABLE_CELL, SHELVE_CELL
from models import GTLibraryGridWarehouse
import inspect

WAREHOUSE_JSON_FILE_FORMAT_VERSION = '2.0'


class GlobalTabbingFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(self, 'min_stack_length'):
            self.min_stack_length = len(inspect.stack())
        record.tabs = '  ' * 2 * (len(inspect.stack()) - self.min_stack_length)
        return True


global_tabbing_filter_instance = GlobalTabbingFilter()


def configure_logger(logger, logging_level=logging.DEBUG):
    logger.setLevel(logging_level)
    logger.addFilter(global_tabbing_filter_instance)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(name)-12s | %(levelname)-8s | %(asctime)-30s | %(tabs)s %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging_level)
    logger.addHandler(handler)
    return logger


logger = logging.getLogger(os.path.basename(__file__))
logger = configure_logger(logger)


def get_warehouse(warehouse_file_path):
    """ Loads the given JSON file and returns a GTLibraryGridWarehouse instance. """

    with open(warehouse_file_path) as f:
        warehouse_data = json.load(f)

    assert warehouse_data['version'] == WAREHOUSE_JSON_FILE_FORMAT_VERSION

    layout = warehouse_data['warehouseLayout']

    return GTLibraryGridWarehouse(
        dimensions=(layout['numRows'], layout['numCols']),
        navigation_grid=layout['navigationGrid'],
        column_tags_to_navigation_grid_coordinates=layout['columnTagsToNavigationGridCoordinates'],
        book_dicts=warehouse_data['books'],
    )


def convert_grid_to_graph(gt_library_grid, unit_cost=1):
    """ Converts navigation grid into a graph where neighboring cells are connected. """
    G = nx.MultiDiGraph()

    num_rows = len(gt_library_grid)
    num_cols = len(gt_library_grid[0])

    # Add all navigable cells to the warehouse library grid
    for r in range(num_rows):
        for c in range(num_cols):
            # Skip navigable cells like book locations or obstacles
            if gt_library_grid[r][c] is not NAVIGABLE_CELL:
                continue

            # Only add navigable cells
            G.add_node((r, c))

    # For each pair of navigable cells in the
    for n1, n2 in itertools.combinations(G.nodes, 2):
        if are_neighbors_in_grid(n1, n2):
            G.add_edge(n1, n2, weight=unit_cost)
            G.add_edge(n2, n1, weight=unit_cost)

    return G


def get_navigable_cell_coordinate_near_book(book_coordinate, gt_library_warehouse):
    """ Returns the navigable cell closest to the given book coordinate. """
    book_coordinate_r, book_coordinate_c = book_coordinate

    # Use the book's shelve aisle to determine where the nearest navigable cell is
    column_tag = gt_library_warehouse.get_column_tag_from_row_and_col(book_coordinate_r, book_coordinate_c)
    aisle_tag = get_aisle_tag_from_column_tag(column_tag)

    if aisle_tag in ('A', 'C', 'E', 'G'):
        # Then, look to the cell below
        return (book_coordinate_r + 1, book_coordinate_c)

    elif aisle_tag in ('B', 'D', 'F'):
        # Then, book to the cell above
        return (book_coordinate_r - 1, book_coordinate_c)


def are_neighbors_in_grid(coordinate_a, coordinate_b):
    """ Determines if the given cells are neighbors or not. """
    coordinate_a_r, coordinate_a_c = coordinate_a
    coordinate_b_r, coordinate_b_c = coordinate_b

    if abs(coordinate_a_r - coordinate_b_r) == 1 and coordinate_a_c == coordinate_b_c:
        return True

    if coordinate_a_r == coordinate_b_r and abs(coordinate_a_c - coordinate_b_c) == 1:
        return True

    return False


def get_subgraph_on_book_locations(gt_library_warehouse, book_locations, source_location):
    """
    Given a list of book locations, this method produces the sub-graph on the navigation grid of these book locations.
    """

    # Ensure the source cell is navigable
    assert gt_library_warehouse.get_cell(source_location[0], source_location[1]) is NAVIGABLE_CELL, \
        "Source must be navigable."

    # Ensure all the books are on shelves
    for book_location_r, book_location_c in book_locations:
        assert gt_library_warehouse.get_cell(book_location_r, book_location_c) is SHELVE_CELL, \
            "Book must be on a shelve."

    G_library = convert_grid_to_graph(gt_library_warehouse.navigation_grid)

    G_subgraph = nx.MultiDiGraph()
    G_subgraph.add_node(source_location)
    G_subgraph.add_nodes_from(book_locations)

    # Connect each book to each other book
    for location1, location2 in itertools.combinations(G_subgraph.nodes, 2):
        if location1 == source_location:
            cell1_location = location1
        else:
            cell1_location = get_navigable_cell_coordinate_near_book(location1, gt_library_warehouse)

        if location2 == source_location:
            cell2_location = location2
        else:
            cell2_location = get_navigable_cell_coordinate_near_book(location2, gt_library_warehouse)

        def map_so(x, a, b, c, d):
            """ https://stackoverflow.com/questions/345187/math-mapping-numbers """
            y = (x - a) / (b - a) * (d - c) + c
            return y


        def library_layout(G_library: nx.Graph):
            MIN_ROW = 0
            MAX_ROW = 24

            MIN_COL = 0
            MAX_COL = 11

            position_dict = {}
            for node in G_library.nodes:
                r, c = node
                position_dict[node] = (
                    map_so(r, MIN_ROW, MAX_ROW, -1, 1),
                    map_so(c, MIN_COL, MAX_COL, -1, 1)
                )

            return position_dict

        ### CHECK LAYOUT HERE
        # import matplotlib.pyplot as plt
        # fig = plt.figure(figsize=(20, 20))
        # pos = library_layout(G_library)
        #
        #
        #
        # nx.draw_networkx_nodes(G_library, pos)
        # nx.draw_networkx_labels(G_library, pos)
        # nx.draw_networkx_edges(G_library, pos)
        # plt.show()

        # Use Dijkstra's algorithm to determine the distance between adjacent shelves
        shortest_path_cost = nx.dijkstra_path_length(G_library, cell1_location, cell2_location)

        G_subgraph.add_edge(location1, location2, weight=shortest_path_cost)
        G_subgraph.add_edge(location2, location1, weight=shortest_path_cost)

    return G_subgraph


def get_pick_path_in_library(gt_library_warehouse, optimal_pick_path_locations, source_coordinate):
    """ Given the TSP shelve locations, this method returns the actual cell-by-cell pick path in the warehouse. """

    G_library = convert_grid_to_graph(gt_library_warehouse.navigation_grid)

    optimal_pick_paths_in_library = []

    # Get the cell-by-cell path between every pair of adjacent nodes in the optimal pick path
    for i in range(len(optimal_pick_path_locations) - 1):
        n1 = optimal_pick_path_locations[i]
        n2 = optimal_pick_path_locations[i + 1]

        if n1 == source_coordinate:
            c1 = source_coordinate
        else:
            c1 = get_navigable_cell_coordinate_near_book(n1, gt_library_warehouse)

        if n2 == source_coordinate:
            c2 = source_coordinate
        else:
            c2 = get_navigable_cell_coordinate_near_book(n2, gt_library_warehouse)

        # Use dijkstra's algorithm to get the best path in the library
        path = nx.dijkstra_path(G_library, c1, c2)

        if n1 != source_coordinate:
            path = [n1] + path

        if n2 != source_coordinate:
            path = path + [n2]

        optimal_pick_paths_in_library.append(path)

    for i in range(len(optimal_pick_paths_in_library)):
        optimal_pick_paths_in_library[i] = shortcut_paths(gt_library_warehouse, optimal_pick_paths_in_library[i])

    return optimal_pick_paths_in_library


def shortcut_paths(gt_library_warehouse, cell_by_cell_book_to_book_path):
    logger.debug('Shortcutting path with %d cells.' % len(cell_by_cell_book_to_book_path))

    shortcut_path = []

    # Remove the 0th and last cells from consideration
    # because we want to keep those no matter what
    cell_by_cell_navigable_path = cell_by_cell_book_to_book_path[1:-1]

    i = 0
    while i < len(cell_by_cell_navigable_path):

        j = i
        farthest_clear_shot_index = j

        while j < len(cell_by_cell_navigable_path):

            current_cell = cell_by_cell_navigable_path[i]
            proposed_shortcut_cell = cell_by_cell_navigable_path[j]

            if gt_library_warehouse.is_clear_shot(current_cell, proposed_shortcut_cell):
                # Keep looking forward
                farthest_clear_shot_index = j
            # else:
            #     # The clear shot has ended, so set the variable one back and shortcut the path
            #     farthest_clear_shot_index -= 1
            #     break

            j += 1

        shortcut_path.append(cell_by_cell_navigable_path[farthest_clear_shot_index])

        i = farthest_clear_shot_index + 1

    shortcut_path = cell_by_cell_book_to_book_path[:2] + shortcut_path + cell_by_cell_book_to_book_path[-1:]

    logger.debug('Path now has %d cells.' % len(shortcut_path))

    return shortcut_path


def reintroduce_duplicate_column_locations(books_and_locations, source, optimal_pick_path):
    locations_to_books = {source: []}
    for book, location in books_and_locations:
        if location not in locations_to_books:
            locations_to_books[location] = []
        locations_to_books[location].append(book)

    books = [None]
    new_path = [source]
    for location in optimal_pick_path:
        # Introduce the location to the new path for how many ever copies of the location are in the path
        for book in locations_to_books[location]:
            books.append(book)
            new_path.append(location)

    books.append(None)
    new_path.append(source)

    return tuple(books), tuple(new_path)


def assert_library_pick_path_is_proper(optimal_pick_path_in_library, optimal_pick_path, source):
    # Ensure the start and end positions are proper
    for i, pick_path in enumerate(optimal_pick_path_in_library):
        expected_path_beginning = source if i == 0 else optimal_pick_path[i]
        expected_path_ending = source if i == len(optimal_pick_path_in_library) - 1 else optimal_pick_path[i + 1]

        assert pick_path[0] == expected_path_beginning
        assert pick_path[-1] == expected_path_ending

    # Ensure every step is one cell away
    # for pick_path in optimal_pick_path_in_library:
    #     for i in range(len(pick_path) - 1):
    #         curr_x, curr_y = pick_path[i]
    #         next_x, next_y = pick_path[i + 1]
    #
    #         assert abs(curr_x - next_x) + abs(curr_y - next_y) == 1


def assert_library_pick_path_has_cost(optimal_library_pick_path, expected_cost, number_of_books):
    actual_cost = 0
    # Ensure every step is one cell away
    for pick_path in optimal_library_pick_path:
        for i in range(len(pick_path) - 1):
            curr_x, curr_y = pick_path[i]
            next_x, next_y = pick_path[i + 1]

            actual_cost += distance((curr_x, curr_y), (next_x, next_y))

    # Every book adds two extra steps (move to book cell, move away from book cell)
    actual_cost -= number_of_books * 2

    assert actual_cost <= expected_cost


def get_pick_path_as_dict(unordered_books, unordered_books_locations, ordered_books, ordered_locations_optimal,
                          optimal_pick_path_in_library):
    unordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in
                                     zip(unordered_books, unordered_books_locations)]
    ordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in
                                   zip(ordered_books[1:-1], ordered_locations_optimal[1:-1])]

    ordered_pick_path = []
    for j in range(len(optimal_pick_path_in_library)):

        if j == len(optimal_pick_path_in_library) - 1:
            target_book, target_location = None, None
        else:
            target_book, target_location = ordered_books[j + 1].as_dict(), ordered_locations_optimal[j + 1]

        ordered_pick_path.append({
            'stepNumber': j + 1,
            'cellByCellPathToTargetBookLocation': optimal_pick_path_in_library[j],
            'targetBookAndTargetBookLocation': {
                'book': target_book,
                'location': target_location
            },
        })

    return {
        'unorderedBooksAndLocations': unordered_books_and_locations,
        'orderedBooksAndLocations': ordered_books_and_locations,
        'orderedPickPath': ordered_pick_path,
    }


def get_aisle_tag_from_column_tag(column_tag):
    return column_tag[0]


def distance(p1, p2):
    return (((p2[0] - p1[0]) ** 2) + ((p2[1] - p1[1]) ** 2)) ** 0.5


def dotProduct(p1, p2):
    return (p1[0] * p2[0]) + (p1[1] * p2[1])


# Return minimum distance between line segment and point
def minimumDistance(line, point):
    d2 = distance(line[1], line[0]) ** 2.0
    if d2 == 0.0:
        return distance(point, line[0])
    # Consider the line extending the segment, parameterized as line[0] + t (line[1] - line[0]).
    # We find projection of point p onto the line.
    # It falls where t = [(point-line[0]) . (line[1]-line[0])] / |line[1]-line[0]|^2
    p1 = (point[0] - line[0][0], point[1] - line[0][1])
    p2 = (line[1][0] - line[0][0], line[1][1] - line[0][1])
    t = dotProduct(p1, p2) / d2  # numpy.dot(p1, p2) / d2
    if t < 0.0:
        return distance(point, line[0])  # Beyond the line[0] end of the segment
    elif t > 1.0:
        return distance(point, line[1])  # Beyond the line[1] end of the segment
    p3 = (line[0][0] + (t * (line[1][0] - line[0][0])),
          line[0][1] + (t * (line[1][1] - line[0][1])))  # projection falls on the segment
    return distance(point, p3)
