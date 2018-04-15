import Tkinter as tk
from models import GTLibraryGridWarehouse
from constants import SHELVE_CELL, NAVIGABLE_CELL, OBSTACLE_CELL
import utils
import json
import os
import logging

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.configure_logger(logger)


VERSION = '1.1'

SQUARE_SIDE_LENGTH = 15

TITLE_TEXT_HEIGHT = 30


class Colors(str):
    """
    Colors based on "Apple Human Interface Guidelines - Colors"
    (https://developer.apple.com/ios/human-interface-guidelines/visual-design/color/)
    """

    NAVIGABLE_CELL = '#fff'
    OBSTACLE_CELL = '#aaa'
    SHELVE_CELL = '#ffcc00'
    PATH_CELL = '#007aff'
    TARGET_BOOK_CELL = '#4cd964'

    TITLE_FONT = '#5856d6'

    CHEVRON = '#ff3b30'


class Direction(str):
    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'


""" Tkinter frame setup. """

tk_main = tk.Tk()


def render():  # type: (GTLibraryGridWarehouse, dict) -> None
    """ Renders the given pick path on the provided grid warehouse into Tkinter main window. """

    logger.info('Starting render.')

    global gt_library_grid_warehouse, canvas_height, canvas_width, canvas, pick_paths, current_pick_path_index

    pick_path = pick_paths[current_pick_path_index]

    canvas.delete('all')

    # Draw column lines
    for col_idx in range(gt_library_grid_warehouse.num_cols):
        col_px = col_idx * SQUARE_SIDE_LENGTH
        canvas.create_line(col_px, 0, col_px, canvas_height - TITLE_TEXT_HEIGHT)

    # Draw row lines
    for row_idx in range(gt_library_grid_warehouse.num_rows):
        row_px = row_idx * SQUARE_SIDE_LENGTH
        canvas.create_line(0, row_px, canvas_width, row_px)

    # Draw obstacles, shelves, and navigable cells
    for r in range(gt_library_grid_warehouse.num_rows):
        for c in range(gt_library_grid_warehouse.num_cols):
            cell = gt_library_grid_warehouse.get_cell(r, c)

            if cell is SHELVE_CELL:
                color = Colors.SHELVE_CELL
            elif cell is NAVIGABLE_CELL:
                color = Colors.NAVIGABLE_CELL
            elif cell is OBSTACLE_CELL:
                color = Colors.OBSTACLE_CELL
            else:
                raise ValueError('Unknown cell type %s' % str(cell))

            canvas.create_rectangle(
                c * SQUARE_SIDE_LENGTH,
                r * SQUARE_SIDE_LENGTH,
                (c + 1) * SQUARE_SIDE_LENGTH,
                (r + 1) * SQUARE_SIDE_LENGTH,
                fill=color)

    # Draw pick paths
    for path_component in pick_path['pickPathInformation']['orderedPickPath']:
        cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']

        for i in range(len(cell_by_cell_path_to_target_book_location)):
            current_cell = cell_by_cell_path_to_target_book_location[i]

            direction = None
            if i < len(cell_by_cell_path_to_target_book_location) - 1:
                direction = get_chevron_direction_between_locations(current_cell, cell_by_cell_path_to_target_book_location[i + 1])

            current_cell_r, current_cell_c = current_cell

            canvas.create_rectangle(
                current_cell_c * SQUARE_SIDE_LENGTH,
                current_cell_r * SQUARE_SIDE_LENGTH,
                (current_cell_c + 1) * SQUARE_SIDE_LENGTH,
                (current_cell_r + 1) * SQUARE_SIDE_LENGTH,
                fill=Colors.PATH_CELL)

            # Draw direction arrow
            triangle_points = get_triangle_coordinates(
                ((current_cell_c + 0.5) * SQUARE_SIDE_LENGTH,
                 (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH),
                direction)
            canvas.create_polygon(*triangle_points, fill=Colors.CHEVRON)

    # Draw target books
    for path_component in pick_path['pickPathInformation']['orderedPickPath']:
        target_book_and_location = path_component['targetBookAndTargetBookLocation']
        target_location = target_book_and_location['location']

        if not target_location:
            continue

        target_location_r, target_location_c = target_book_and_location['location']

        canvas.create_rectangle(
            target_location_c * SQUARE_SIDE_LENGTH,
            target_location_r * SQUARE_SIDE_LENGTH,
            (target_location_c + 1) * SQUARE_SIDE_LENGTH,
            (target_location_r + 1) * SQUARE_SIDE_LENGTH,
            fill=Colors.TARGET_BOOK_CELL)

    # Draw pick path ID
    canvas.create_text(
        10,
        canvas_height - TITLE_TEXT_HEIGHT / 2,
        anchor=tk.W,
        fill=Colors.TITLE_FONT,
        font='Calibri 12 bold',
        text='Path ID %02d - %s' % (pick_path['pathId'], pick_path['pathType'].title()))

    canvas.update()

    logger.info('Finished render.')


def get_chevron_direction_between_locations(location_a, location_b):
    location_a_r, location_a_c = location_a
    location_b_r, location_b_c = location_b

    if location_a_r > location_b_r and location_a_c == location_b_c:
        return Direction.UP
    elif location_a_r < location_b_r and location_a_c == location_b_c:
        return Direction.DOWN
    elif location_a_r == location_b_r and location_a_c > location_b_c:
        return Direction.LEFT
    elif location_a_r == location_b_r and location_a_c < location_b_c:
        return Direction.RIGHT
    else:  # points are equal
        raise ValueError()


def get_triangle_coordinates(origin_location, direction):
    """ Creates points for a triangle in the given direction centered at the given origin. """

    a_x, a_y = origin_location
    b_x, b_y = origin_location
    c_x, c_y = origin_location

    # This is how many pixels each point will be offset in the x or y direction
    chevron_offset_px = SQUARE_SIDE_LENGTH / 4

    if direction is Direction.UP:
        a_x -= chevron_offset_px
        a_y += chevron_offset_px

        b_x += chevron_offset_px
        b_y += chevron_offset_px

        c_y -= chevron_offset_px

    elif direction is Direction.DOWN:
        a_x += chevron_offset_px
        a_y -= chevron_offset_px

        b_x -= chevron_offset_px
        b_y -= chevron_offset_px

        c_y += chevron_offset_px

    elif direction is Direction.RIGHT:
        a_x -= chevron_offset_px
        a_y -= chevron_offset_px

        b_x -= chevron_offset_px
        b_y += chevron_offset_px

        c_x += chevron_offset_px

    elif direction is Direction.LEFT:
        a_x += chevron_offset_px
        a_y += chevron_offset_px

        b_x += chevron_offset_px
        b_y -= chevron_offset_px

        c_x -= chevron_offset_px

    else:
        pass

    return (a_x, a_y), (b_x, b_y), (c_x, c_y)


def tk_handle_left_key(event):
    global current_pick_path_index
    current_pick_path_index = max(0, current_pick_path_index - 1)

    logger.info("Left key pressed. Current pick path index set to %d." % current_pick_path_index)

    render()


def tk_handle_right_key(event):
    global current_pick_path_index
    current_pick_path_index = min(len(pick_paths) - 1, current_pick_path_index + 1)

    logger.info("Right key pressed. Current pick path index set to %d." % current_pick_path_index)

    render()


if __name__ == '__main__':
    global gt_library_grid_warehouse
    gt_library_grid_warehouse = utils.get_warehouse('warehouse.json')

    global canvas_width, canvas_height
    canvas_width = gt_library_grid_warehouse.num_cols * SQUARE_SIDE_LENGTH
    canvas_height = gt_library_grid_warehouse.num_rows * SQUARE_SIDE_LENGTH + TITLE_TEXT_HEIGHT

    global canvas
    canvas = tk.Canvas(
        master=tk_main,
        width=canvas_width,
        height=canvas_height)
    canvas.pack()

    with open('pick-paths.json', mode='r') as f:
        pick_path_data = json.load(f)

    assert pick_path_data['version'] == VERSION

    global pick_paths, current_pick_path_index
    pick_paths = pick_path_data['pickPaths']
    current_pick_path_index = 0

    tk_main.bind('<Left>', tk_handle_left_key)
    tk_main.bind('<Right>', tk_handle_right_key)

    render()
    tk_main.mainloop()
