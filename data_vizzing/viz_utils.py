import os
import matplotlib.pyplot as plt

def save_and_show_plot(figure, filename, folder="plots", show=False, **kwargs):
    """
    Saves a matplotlib figure to a folder and optionally displays it.
    
    Parameters:
        figure: Matplotlib figure object
        filename: Name of the file to save (e.g., 'my_plot.png')
        folder: Directory to save the plot (default: 'plots')
        show: Whether to display the plot using plt.show()
        **kwargs: Additional arguments for `savefig` (e.g., dpi, format)
    """
    # Ensure the folder exists
    os.makedirs(folder, exist_ok=True)
    
    # Construct the full path
    filepath = os.path.join(folder, filename)
    
    # Save the figure
    figure.savefig(filepath, **kwargs)
    print(f"Plot saved to {filepath}")
    
    # Optionally display the plot
    if show:
        plt.show()
