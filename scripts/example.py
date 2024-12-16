import matplotlib.pyplot as plt
import numpy as np
from data_vizzing.viz_utils import save_and_show_plot

# Generate some example data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create a plot
fig, ax = plt.subplots()
ax.plot(x, y)
ax.set_title("Example Plot")

# Save and optionally display the plot
save_and_show_plot(fig, "example_plot.png", dpi=300, show=True)
