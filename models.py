NAVIGABLE_CELL = None


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
