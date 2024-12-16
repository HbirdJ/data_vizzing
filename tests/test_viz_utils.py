import os
import matplotlib.pyplot as plt
from data_vizzing.viz_utils import save_and_show_plot

def test_save_and_show_plot():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])

    save_and_show_plot(fig, "test_plot.png", show=False)
    assert os.path.exists("plots/test_plot.png")
