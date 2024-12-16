
# Electrify America Charging Analytics

This repository processes and visualizes charging session data from Electrify America. It extracts data from `.eml` email files and generates informative graphs to analyze charging speed, efficiency, and environmental factors like temperature.

---

## Features

- Extracts charging session data from `.eml` files.
- Calculates effective charging speeds, starting/ending battery states, and more.
- Visualizes charging data with detailed, styled plots.

---

## Requirements

- Python 3.10+
- Poetry for dependency management.

Install Poetry using:
```bash
pip install poetry
```

---

## Installation

Install the project dependencies using Poetry:
```bash
poetry install
```

This will set up the environment and install all required packages.

---

## Usage

### 1. Prepare the Data
- Save your Electrify America charging session summary emails as `.eml` files.
- Place the `.eml` files in the directory:
  ```
  /data/electrify_america/easessionsummaries/
  ```

### 2. Generate the Graphs
Run the plotting script to process the emails and generate visualizations:
```bash
poetry run python scripts/ea_plotting.py
```

This will generate graphs and save them as image files in the project directory.

---

## Output

The script produces visualizations that include:
1. Effective charging speeds.
2. Start and end state-of-charge percentages.
3. Correlation between temperature and charging efficiency.

Graphs are saved as `.png` files and can be customized for further analysis.