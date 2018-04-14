from constants import SHELVE_CELL, OBSTACLE_CELL, NAVIGABLE_CELL
import copy


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


class ShelvingColumn(object):
    def __init__(self, aisle, column):
        self.aisle = aisle
        self.column = str(column)
        self.books = []

    def add_books_from_repository(self, repository):
        books = []
        for book_tag in repository:
            book = repository[book_tag]
            if book.aisle == self.aisle and book.column == self.column:
                books.append(book)

        self.books = sorted(books, key=lambda b: b.row)

    def __iter__(self):
        return iter(self.books)


class LibraryRow(object):
    def __init__(self, aisle):
        self.aisle = aisle

        if self.aisle in ('A', 'C', 'E', 'G'):
            self.starting_column_number = 100
            self.ending_column_number = 110
        elif self.aisle in ('B', 'D', 'F', 'H'):
            self.starting_column_number = 101
            self.ending_column_number = 111
        else:
            raise ValueError("Unknown aisle %s" % self.aisle)

    def get_shelving_columns(self, books_repository):
        shelving_columns = []
        step = 2
        for column_number in range(self.starting_column_number, self.ending_column_number + 1, step):
            shelving_column = ShelvingColumn(self.aisle, column_number)
            shelving_column.add_books_from_repository(books_repository)
            shelving_columns.append(shelving_column)
        return shelving_columns


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

        # Update navigation grid to include shelves at their specified locations
        assert len(shelve_tags_to_locations) == self.NUMBER_OF_SHELVES
        # for shelve_tag, location in shelve_tags_to_locations.iteritems():
        #     row_idx, col_idx = location
        #     assert self.navigation_grid[row_idx][col_idx] == SHELVE_CELL
        #     self.navigation_grid[row_idx][col_idx] = shelve_tag
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
