from constants import SHELVE_CELL, OBSTACLE_CELL, NAVIGABLE_CELL
import copy
import numpy as np
from constants import SUBJECT_RADIUS


class Book(object):
    def __init__(self, title, author, aisle, column, row):
        self.title = title
        self.author = author
        self.aisle = aisle
        self.column = column
        self.row = row

    @property
    def tag(self):
        return "D-%s-%s-%s" % (self.aisle, self.column, self.row)

    @property
    def shelve_tag(self):
        return "D-%s-%s" % (self.aisle, self.column)

    def __str__(self):
        return "%s: %s by %s" % (self.tag, self.title, self.author)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def as_dict(self):
        return {
            "title": self.title,
            "author": self.author,
            "tag": self.tag,
        }


class GTLibraryGridWarehouse(object):
    NUMBER_OF_SHELVES = 6 * 8

    def __init__(self, dimensions, navigation_grid, shelve_tags_to_locations, book_dicts):

        self.dimensions = dimensions
        num_rows, num_cols = dimensions

        self.navigation_grid = copy.deepcopy(navigation_grid)
        assert len(navigation_grid) == num_rows
        assert len(navigation_grid[0]) == num_cols

        for row in navigation_grid:
            for cell in row:
                assert cell == NAVIGABLE_CELL \
                       or cell == OBSTACLE_CELL \
                       or cell == SHELVE_CELL

        assert len(shelve_tags_to_locations) == self.NUMBER_OF_SHELVES
        self.locations_to_shelve_tags = {tuple(location): tag for tag, location in shelve_tags_to_locations.iteritems()}

        self.books = []
        for book_dict in book_dicts:
            self.books.append(Book(
                title=book_dict['book']['title'],
                author=book_dict['book']['author'],
                aisle=book_dict['location']['aisle'],
                column=book_dict['location']['column'],
                row=book_dict['location']['row'],
            ))

    @property
    def num_rows(self):
        return self.dimensions[0]

    @property
    def num_cols(self):
        return self.dimensions[1]

    def get_book_location(self, target_book):
        """ Given a Book instance, this method finds the (r, c) location of the book in this warehouse. """

        for r in range(self.num_rows):
            for c in range(self.num_cols):

                # Only examine shelve cells
                cell = self.get_cell(r, c)
                if cell is not SHELVE_CELL:
                    continue

                shelve_tag_at_location = self.get_shelve_tag(r, c)

                if shelve_tag_at_location == target_book.shelve_tag:
                    return (r, c)

        # raise ValueError("Couldn't find book with tag %s" % target_book.tag)

    def get_books_locations(self, target_books):
        book_locations = []

        for target_book in target_books:
            book_locations.append(self.get_book_location(target_book))

        return book_locations

    def get_cell(self, row, col):
        return self.navigation_grid[row][col]

    def get_shelve_tag(self, row, col):
        return self.locations_to_shelve_tags.get((row, col), None)

    def is_clear_shot(self, location_a, location_b, radius=SUBJECT_RADIUS):

        assert radius > 0.0

        assert self.get_cell(*location_a) in (NAVIGABLE_CELL, SHELVE_CELL)
        assert self.get_cell(*location_b) in (NAVIGABLE_CELL, SHELVE_CELL)

        if location_a == location_b:
            return True

        import utils

        path_line = location_a, location_b

        cell_border_offsets = [
            (0, 0),
            (0, 1),
            (1, 1),
            (1, 0),
        ]

        for r in range(self.num_rows):
            for c in range(self.num_cols):

                for offset_r, offset_c in cell_border_offsets:

                    new_r, new_c = r + offset_r, c + offset_c

                    if new_r < 0 or new_r >= self.num_rows or new_c < 0 or new_c >= self.num_cols:
                        continue

                    if utils.minimumDistance(path_line, (new_r, new_c)) <= radius:
                        if self.get_cell(new_r, new_c) is not NAVIGABLE_CELL:
                            return False

        return True
