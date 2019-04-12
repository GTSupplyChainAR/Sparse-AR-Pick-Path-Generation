import json
import os
import csv

if __name__ == '__main__':

    """ Converts the books.csv file into the books.json file. """
    json_dicts = []
    with open('books.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            json_dicts.append({
                'location': {
                    'aisle': row['location/aisle'],
                    'column': row['location/column'],
                    'row': row['location/row'],
                },
                'book': {
                    'title': row['title'],
                    'author': row['author'],
                }
            })
    with open('books.json', mode='w') as jsonfile:
        json.dump(json_dicts, jsonfile, indent=4)
