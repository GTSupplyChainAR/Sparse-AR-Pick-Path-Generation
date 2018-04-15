# Sparse-AR-Pick-Path-Generation
Script to generate order pick paths for a sparse AR study

## Installation

```
git clone https://github.com/GTSupplyChainAR/Sparse-AR-Pick-Path-Generation.git pick-path-gen
cd pick-path-gen
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```
python main.py
```

This script will write information about pick paths to `output.json`.

Alter the parameters hardcoded in `main.py` like 
* the number of training tasks, or
* the number of testing tasks,
* the number of books per pick path.

## Visualizations

You can view the pick paths using
```
python visualize.py
```

Navigate to other pick paths using the left and right arrow keys.

## Output description

The format of the `output.json` file should be very simple and intuitive. Please, ask one a team member for more details.
