import json
from models import Book, NAVIGABLE_CELL
import networkx as nx
import itertools


def get_books_repository(filepath):
    books = []

    with open(filepath) as f:
        book_dicts = json.load(f)

    for book_dict in book_dicts:
        books.append(Book(
            title=book_dict['book']['title'],
            author=book_dict['book']['author'],
            aisle=book_dict['location']['aisle'],
            column=book_dict['location']['column'],
            row=book_dict['location']['row'],
        ))

    return {book.tag: book for book in books}


def get_books_locations(books, gt_library):
    locations = []
    for selected_book in books:
        locations.append(get_book_location(selected_book, gt_library))
    return books, locations


def get_book_location(target_book, gt_library):
    num_rows = len(gt_library)
    num_cols = len(gt_library[0])

    for r in range(num_rows):
        for c in range(num_cols):
            cell = gt_library[r][c]
            if cell is NAVIGABLE_CELL:
                continue

            for book in cell:
                if book.tag == target_book.tag:
                    return (r, c)

    raise ValueError("Couldn't find book with tag %s" % target_book.tag)


def convert_grid_to_graph(gt_library, unit_cost=1):
    G = nx.MultiDiGraph()

    num_rows = len(gt_library)
    num_cols = len(gt_library[0])

    for r in range(num_rows):
        for c in range(num_cols):
            if gt_library[r][c] is not NAVIGABLE_CELL:
                continue

            G.add_node((r, c))

    for n1, n2 in itertools.combinations(G.nodes, 2):
        if are_neighbors_in_grid(n1, n2):
            G.add_edge(n1, n2, weight=unit_cost)
            G.add_edge(n2, n1, weight=unit_cost)

    return G


def get_naviable_cell_coordinate_near_book(book_coordinate, library):
    book_coordinate_r, book_coordinate_c = book_coordinate
    shelving_column = library[book_coordinate_r][book_coordinate_c]

    if shelving_column.aisle in ('A', 'C', 'E', 'G'):
        # Then, look to the cell above
        return (book_coordinate_r - 1, book_coordinate_c)
    elif shelving_column.aisle in ('B', 'D', 'F', 'H'):
        # Then, book to the cell below
        return (book_coordinate_r + 1, book_coordinate_c)


def are_neighbors_in_grid(n1, n2):
    x1, y1 = n1
    x2, y2 = n2

    if abs(x1 - x2) == 1 and y1 == y2:
        return True

    if x1 == x2 and abs(y1 - y2) == 1:
        return True

    return False


def get_subgraph_on_book_locations(libray, book_locations, source_location):

    if libray[source_location[0]][source_location[1]] is not NAVIGABLE_CELL:
        raise ValueError("Source must be navigable.")

    G_library = convert_grid_to_graph(libray)

    G_subgraph = nx.MultiDiGraph()
    G_subgraph.add_node(source_location)
    G_subgraph.add_nodes_from(book_locations)

    # Connect each book to each other book
    for location1, location2 in itertools.combinations(G_subgraph.nodes, 2):
        if location1 == source_location:
            cell1_location = location1
        else:
            cell1_location = get_naviable_cell_coordinate_near_book(location1, libray)

        if location2 == source_location:
            cell2_location = location2
        else:
            cell2_location = get_naviable_cell_coordinate_near_book(location2, libray)

        shortest_path_cost = nx.dijkstra_path_length(G_library, cell1_location, cell2_location)

        G_subgraph.add_edge(location1, location2, weight=shortest_path_cost)
        G_subgraph.add_edge(location2, location1, weight=shortest_path_cost)

    return G_subgraph


def get_pick_path_in_library(library, books, optimal_pick_path_locations, source_coordinate):
    G_library = convert_grid_to_graph(library)

    optimal_pick_path_in_library = []

    for i in range(len(optimal_pick_path_locations) - 1):
        n1 = optimal_pick_path_locations[i]
        n2 = optimal_pick_path_locations[i + 1]

        if n1 == source_coordinate:
            c1 = source_coordinate
        else:
            c1 = get_naviable_cell_coordinate_near_book(n1, library)

        if n2 == source_coordinate:
            c2 = source_coordinate
        else:
            c2 = get_naviable_cell_coordinate_near_book(n2, library)

        path = nx.dijkstra_path(G_library, c1, c2)

        if n1 != source_coordinate:
            path = [n1] + path

        if n2 != source_coordinate:
            path = path + [n2]

        optimal_pick_path_in_library.append(path)

    return optimal_pick_path_in_library


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
    for pick_path in optimal_pick_path_in_library:
        for i in range(len(pick_path) - 1):
            curr_x, curr_y = pick_path[i]
            next_x, next_y = pick_path[i + 1]

            assert abs(curr_x - next_x) + abs(curr_y - next_y) == 1


def assert_library_pick_path_has_cost(optimal_library_pick_path, expected_cost, number_of_books):
    actual_cost = 0
    # Ensure every step is one cell away
    for pick_path in optimal_library_pick_path:
        for i in range(len(pick_path) - 1):
            curr_x, curr_y = pick_path[i]
            next_x, next_y = pick_path[i + 1]

            actual_cost += abs(curr_x - next_x) + abs(curr_y - next_y)

    # Every book adds two extra steps (move to book cell, move away from book cell)
    actual_cost -= number_of_books * 2

    assert expected_cost == actual_cost


def get_pick_path_as_dict(unordered_books, unordered_books_locations, ordered_books, ordered_locations_optimal, optimal_pick_path_in_library):
    unordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in zip(unordered_books, unordered_books_locations)]
    ordered_books_and_locations = [{'book': book.as_dict(), 'location': location} for book, location in zip(ordered_books[1:-1], ordered_locations_optimal[1:-1])]

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
