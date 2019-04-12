try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

from constants import SHELVE_CELL, NAVIGABLE_CELL, OBSTACLE_CELL
import utils
import json
import os
import logging
import numpy as np

logger = logging.getLogger(os.path.basename(__file__))
logger = utils.configure_logger(logger)

PICK_PATH_FILE_FORMAT_VERSION = '2.0'

# The length of a side on each square in the Tkinter window
SQUARE_SIDE_LENGTH_PX = 15

# The height of the text portion at the bottom of the Tkinter window
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
    PATH_LINE = CHEVRON


# Tkinter setup
tk_main = tk.Tk()


def render():
    """ Renders the given pick path on the provided grid warehouse into Tkinter main window. """

    logger.info('Starting render.')

    # Rely on global variables that can be modified elsewhere
    global gt_library_grid_warehouse, canvas_height, canvas_width, canvas, pick_paths, current_pick_path_index

    # Get pick path to be rendered
    # pick_path = pick_paths[current_pick_path_index]
    # ordered_pick_path = pick_path['pickPathInformation']['orderedPickPath']

    # Remove all elements added in previous calls to render
    canvas.delete('all')

    # Draw column lines
    for col_idx in range(gt_library_grid_warehouse.num_cols):
        col_px = col_idx * SQUARE_SIDE_LENGTH_PX
        canvas.create_line(
            col_px,
            0,
            col_px,
            canvas_height - TITLE_TEXT_HEIGHT)

    # Draw row lines
    for row_idx in range(gt_library_grid_warehouse.num_rows):
        row_px = row_idx * SQUARE_SIDE_LENGTH_PX
        canvas.create_line(0, row_px, canvas_width, row_px)

    # Draw obstacles, shelves, and navigable cells
    for r in range(gt_library_grid_warehouse.num_rows):
        for c in range(gt_library_grid_warehouse.num_cols):
            cell = gt_library_grid_warehouse.get_cell(r, c)

            # Get the right cell color based on the cell's type
            if cell is SHELVE_CELL:
                color = Colors.SHELVE_CELL
            elif cell is NAVIGABLE_CELL:
                color = Colors.NAVIGABLE_CELL
            elif cell is OBSTACLE_CELL:
                color = Colors.OBSTACLE_CELL
            else:
                raise ValueError('Unknown cell type %s' % str(cell))

            canvas.create_rectangle(
                c * SQUARE_SIDE_LENGTH_PX,
                r * SQUARE_SIDE_LENGTH_PX,
                (c + 1) * SQUARE_SIDE_LENGTH_PX,
                (r + 1) * SQUARE_SIDE_LENGTH_PX,
                fill=color)

    # # Draw pick paths
    # for path_component in ordered_pick_path:
    #     cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']
    #
    #     for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location):
    #         current_cell_r, current_cell_c = current_cell
    #
    #         # Draw cell in the path
    #         canvas.create_rectangle(
    #             current_cell_c * SQUARE_SIDE_LENGTH_PX,
    #             current_cell_r * SQUARE_SIDE_LENGTH_PX,
    #             (current_cell_c + 1) * SQUARE_SIDE_LENGTH_PX,
    #             (current_cell_r + 1) * SQUARE_SIDE_LENGTH_PX,
    #             fill=Colors.PATH_CELL,
    #         )
    #
    # # Draw chevrons and path direction lines
    # for path_component in ordered_pick_path:
    #     cell_by_cell_path_to_target_book_location = path_component['cellByCellPathToTargetBookLocation']
    #
    #     for i, current_cell in enumerate(cell_by_cell_path_to_target_book_location):
    #         current_cell_r, current_cell_c = current_cell
    #
    #         # If there is a next cell (we're not at the end) render the arrow and path line
    #         if i >= len(cell_by_cell_path_to_target_book_location) - 1:
    #             continue
    #
    #         next_cell = cell_by_cell_path_to_target_book_location[i + 1]
    #         next_cell_r, next_cell_c = next_cell
    #         direction = get_chevron_angle_transform_for_points(
    #             location_a=(
    #             (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX),
    #             location_b=((next_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX, (next_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX))
    #
    #         triangle_points = get_transformed_chevron(
    #             # 0.5 value centers the triangle origin
    #             origin=(
    #                 (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,  # x
    #                 (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,  # y
    #             ),
    #             transform_angle=direction)
    #
    #         canvas.create_polygon(
    #             *triangle_points,
    #             fill=Colors.CHEVRON)
    #
    #         # Draw line between these two points
    #         canvas.create_line(
    #             (current_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,  # x
    #             (current_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,  # y
    #             (next_cell_c + 0.5) * SQUARE_SIDE_LENGTH_PX,
    #             (next_cell_r + 0.5) * SQUARE_SIDE_LENGTH_PX,
    #             fill=Colors.PATH_LINE,
    #             activedash=True,
    #             dash=True,
    #             width=SQUARE_SIDE_LENGTH_PX / 5
    #         )
    #
    # # Draw target books
    # for path_component in ordered_pick_path:
    #     target_book_and_location = path_component['targetBookAndTargetBookLocation']
    #     target_location = target_book_and_location['location']
    #
    #     if not target_location:
    #         continue
    #
    #     target_location_r, target_location_c = target_book_and_location['location']
    #
    #     canvas.create_rectangle(
    #         target_location_c * SQUARE_SIDE_LENGTH_PX,
    #         target_location_r * SQUARE_SIDE_LENGTH_PX,
    #         (target_location_c + 1) * SQUARE_SIDE_LENGTH_PX,
    #         (target_location_r + 1) * SQUARE_SIDE_LENGTH_PX,
    #         fill=Colors.TARGET_BOOK_CELL)
    #
    # # Draw pick path ID
    # canvas.create_text(
    #     10,  # x offset
    #     canvas_height - TITLE_TEXT_HEIGHT / 2,
    #     anchor=tk.W,
    #     fill=Colors.TITLE_FONT,
    #     font='Calibri 12 bold',
    #     text='Path ID %02d - %s' % (pick_path['pathId'], pick_path['pathType'].title()))

    # Apply changes to canvas
    canvas.update()

    logger.info('Finished render.')


def get_chevron_angle_transform_for_points(location_a, location_b):
    """ Gets the angle transformation from vertical of the chevron (arrow) between the two locations. """
    return angle(location_a, location_b) + (np.pi / float(2))


def angle(a, b):
    a_x, a_y = a
    b_x, b_y = b

    d_y = b_y - a_y
    d_x = b_x - a_x

    return angle_trunc(np.arctan2(d_y, d_x))


def angle_trunc(angle):
    while angle < 0.0:
        angle += np.pi * 2
    return angle


def get_transformed_chevron(origin, transform_angle):
    """ Creates points for a triangle in the given direction centered at the given origin. """

    o_x, o_y = origin

    # This is how many pixels each point will be offset in the x or y direction
    chevron_offset_px = SQUARE_SIDE_LENGTH_PX / 4

    # Compute the upwards direction arrow
    a_x, a_y = o_x - chevron_offset_px, o_y + chevron_offset_px
    b_x, b_y = o_x + chevron_offset_px, o_y + chevron_offset_px
    c_x, c_y = o_x, o_y - chevron_offset_px

    # Pack up the angles
    a, b, c = (a_x, a_y), (b_x, b_y), (c_x, c_y)

    # Apply angle transformation
    a = transform(origin, a, transform_angle)
    b = transform(origin, b, transform_angle)
    c = transform(origin, c, transform_angle)

    return a, b, c


def transform(origin, point, theta):
    """ Transforms the given point by theta radians around the given origin. """

    # Numpy!
    origin = np.array(origin)
    point = np.array(point)

    # Bring point to origin
    point = point - origin

    # Apply transformation
    transformation_matrix = np.array([
        [np.cos(theta), -1 * np.sin(theta)],
        [np.sin(theta), np.cos(theta)]
    ])
    point = np.matmul(transformation_matrix, point)

    # Take point back out from origin
    point = point + origin

    return tuple(point)


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
    # Setup all global variables used by Tkinter callbacks later on

    global gt_library_grid_warehouse
    gt_library_grid_warehouse = utils.get_warehouse('warehouse.json')

    global canvas_width, canvas_height
    canvas_width = gt_library_grid_warehouse.num_cols * SQUARE_SIDE_LENGTH_PX
    canvas_height = gt_library_grid_warehouse.num_rows * SQUARE_SIDE_LENGTH_PX + TITLE_TEXT_HEIGHT

    global canvas
    canvas = tk.Canvas(
        master=tk_main,
        width=canvas_width,
        height=canvas_height)
    canvas.pack()
    canvas.master.title("Sparse AR - Pick Path Visualization - v%s" % PICK_PATH_FILE_FORMAT_VERSION)

    # Setup pick paths, showing the first one

    # with open('pick-paths.json', mode='r') as f:
    #     pick_path_data = json.load(f)
    #
    # assert pick_path_data['version'] == PICK_PATH_FILE_FORMAT_VERSION
    #
    # global pick_paths, current_pick_path_index
    # pick_paths = pick_path_data['pickPaths']
    # current_pick_path_index = 0
    #
    # # Bind Left/Right keypress events to the corresponding functions
    # tk_main.bind('<Left>', tk_handle_left_key)
    # tk_main.bind('<Right>', tk_handle_right_key)

    # Render the first pick path
    render()

    # Run Tkinter forever
    tk_main.mainloop()
