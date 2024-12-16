import os
import re
import csv
from datetime import datetime, timedelta
from email import policy
from email.parser import BytesParser
from meteostat import Point, Hourly
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import pandas as pd
import seaborn as sns
import mplcyberpunk

from data_vizzing.viz_utils import save_and_show_plot


class EmailProcessor:
    def __init__(self, input_dir, output_file, battery_size = 77.4):
        self.input_dir = input_dir
        self.output_file = output_file
        self.battery_size = battery_size

    def extract_charge_metadata(self, email_content, filename):
        """
        Extract metadata from the email content using regex patterns.
        """
        patterns = {
            "Date": r"(\d{2}/\d{2}/\d{4})",  # Matches the date in MM/DD/YYYY format
            "Location Address Block": r"\n([\w\s\(\),-]+?)\n([\d\w\s,-]+?)\n([\w\s,.]+?\d{5})",  # Matches location and address details
            "Charger ID": r"Charger ID: # ([\d\-]+)",
            "Session ID": r"Session: (\d+)",
            "Plan Name": r"Plan Name\s+([\w\s]+)",
            "Charging Price": r"Charging Price\s+\$(\d+\.\d+)/kWh",
            "Session Start Time": r"Session Start Time\s+([\d:APM\s]+)",
            "Session End Time": r"Session End Time\s+([\d:APM\s]+)",
            "Charging Time": r"Charging Time\s+([\d:]+)",
            "Total Energy Delivered": r"Total Energy Delivered\s+([\d.]+) kWh",
            "Energy Billed": r"Energy Billed\s+([\d.]+) kWh",
            "End State of Charge": r"End State of Charge\s+(\d+)",  # No unit (%)
            "Max Charging Speed": r"Max. Charging Speed\s+([\d]+)",  # No unit (kW)
            "Charging Cost": r"Charging Cost\s+\$(\d+\.\d+)",
            "Discount": r"Discount\s+\$(\d+\.\d+)",
            "Total Paid": r"Total Paid: \$(\d+\.\d+)"
        }
        
        metadata = {"Filename": filename}  # Start with filename

        # Extract date
        date_match = re.search(patterns["Date"], email_content)
        metadata["Date"] = date_match.group(1) if date_match else None

        # Extract location and address details
        location_match = re.search(patterns["Location Address Block"], email_content)
        if location_match:
            metadata["Location"] = location_match.group(1).strip()
            metadata["Address"] = f"{location_match.group(2).strip()}, {location_match.group(3).strip()}"
        else:
            metadata["Location"] = metadata["Address"] = None

        # Extract other fields
        for key, pattern in patterns.items():
            if key in ["Location Address Block", "Date"]:  # Skip patterns already handled
                continue
            match = re.search(pattern, email_content)
            if match:
                # Strip unnecessary whitespace and newline characters
                value = match.group(1).strip()
                if key in ["Charging Price", "Charging Cost", "Discount", "Total Paid"]:  # Remove "$"
                    value = value.replace("$", "")
                metadata[key] = value
            else:
                metadata[key] = None

        return metadata

    def calculate_columns(self, metadata):
        """
        Add calculated columns to the metadata.
        """
        # Estimated starting charge assuming 92% efficiency
        try:
            metadata["Estimated Starting Charge"] = round(
                ((float(metadata["End State of Charge"]) / 100 * self.battery_size) - 
                (float(metadata["Total Energy Delivered"]) * .92))
                / self.battery_size * 100, 2
            )
        except (TypeError, ValueError, ZeroDivisionError):
            metadata["Cost Per kWh"] = None

        # Effective Charge Speed
        try:
            # Convert Charging Time "HH:MM:SS" to hours
            h, m, s = map(int, metadata["Charging Time"].split(":"))
            total_hours = h + m / 60 + s / 3600
            metadata["Effective Charging Speed"] = round(
                float(metadata["Total Energy Delivered"]) / total_hours, 2
            )
            metadata["Minutes Charging"] = h * 60 + m + s / 60
        except (TypeError, ValueError, ZeroDivisionError, AttributeError):
            metadata["Effective Charging Speed"] = None
            metadata["Minutes Charging"] = None

        return metadata
    
    def calculate_temp(self, metadata):
        """
        Add the average temperature for the session start time and location.
        """
        try:
            # Extract location and time from metadata
            start_time_str = metadata.get("Session Start Time")
            date_str = metadata.get("Date")
            
            if start_time_str and date_str:
                # Convert start time to a proper datetime object
                start_time = datetime.strptime(f"{date_str} {start_time_str}", "%m/%d/%Y %I:%M:%S %p")
                end_time = start_time + timedelta(hours=1)
                
                # Define coordinates for Denver (this could be refined with geocoding for general use)
                denver_coords = Point(39.7392, -104.9903)  # Latitude, Longitude for Denver
                
                # Fetch hourly weather data for the given time
                weather_data = Hourly(denver_coords, start_time, end_time)
                weather_data = weather_data.fetch()
                
                if not weather_data.empty:
                    metadata["Average Temperature (°C)"] = round(weather_data['temp'].iloc[0], 2)
                else:
                    metadata["Average Temperature (°C)"] = None
            else:
                metadata["Average Temperature (°C)"] = None
        except Exception as e:
            metadata["Average Temperature (°C)"] = None
            print(f"Error fetching temperature data: {e}")

        return metadata

    def plot_charge_events(self):
        data = pd.read_csv(self.output_file)

        # Convert relevant columns to numeric
        data["End State of Charge"] = pd.to_numeric(data["End State of Charge"], errors='coerce')
        data["Estimated Starting Charge"] = pd.to_numeric(data["Estimated Starting Charge"], errors='coerce')
        data["Effective Charging Speed"] = pd.to_numeric(data["Effective Charging Speed"], errors='coerce')
        data["Average Temperature (°C)"] = pd.to_numeric(data["Average Temperature (°C)"], errors='coerce')

        # Convert the Date column to datetime and sort the data
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')  # Convert to datetime
        data = data.sort_values(by='Date')  # Sort by date in ascending order
        data.reset_index(drop=True, inplace=True)  # Reset index

        # Drop rows with missing essential data
        plot_data = data.dropna(subset=["Estimated Starting Charge", "End State of Charge", "Effective Charging Speed", "Average Temperature (°C)"])

        # Normalize temperature for color mapping
        norm = Normalize(
            vmin=plot_data["Average Temperature (°C)"].min(), 
            vmax=plot_data["Average Temperature (°C)"].max()
        )
        cmap = plt.cm.coolwarm
        norm2 = Normalize(
            vmin=plot_data["Effective Charging Speed"].min(), 
            vmax=plot_data["Effective Charging Speed"].max()
        )
        cmap2 = plt.cm.hot

        # Create the bar plot
        plt.style.use("cyberpunk")
        plt.figure(figsize=(12, 12))  # Adjust figure size as needed
        ax = plt.gca()
        

        for i, row in plot_data.iterrows():
            bars = ax.barh(  # Use barh for horizontal bars
                row.name,  # Position on the Y-axis (charge event index)
                row["End State of Charge"] - row["Estimated Starting Charge"],
                left=row["Estimated Starting Charge"], # Left starting point for the bar
                color=cmap(norm(row["Average Temperature (°C)"])),
                edgecolor='k',
                label=None
            )

            # Annotate Effective Charging Speed
            ax.text(
                (row["Estimated Starting Charge"] + row["End State of Charge"]) / 2,  # x position
                row.name,  # y position
                f"{row['Minutes Charging']:.0f} minutes {row['Effective Charging Speed']:.0f} kW (max: {row['Max Charging Speed']:.0f} kW)",
                ha='center', va='center', fontsize=9, color='black', 
                # bbox=dict(facecolor=cmap2(norm2(row['Effective Charging Speed'])), edgecolor='black', boxstyle='round')
            )

            # Annotate Start Percent Charge
            ax.text(
                row["Estimated Starting Charge"] - 1,  # x position (slightly to the left of the bar start)
                row.name,  # y position
                f"~{row['Estimated Starting Charge']:.0f}%",
                ha='right', va='center', fontsize=9, color='blue', backgroundcolor='white'
            )

            # Annotate End Percent Charge
            ax.text(
                row["End State of Charge"] + 1,  # x position (slightly to the right of the bar end)
                row.name,  # y position
                f"{row['End State of Charge']:.0f}%",
                ha='left', va='center', fontsize=9, color='blue', backgroundcolor='white'
            )


        # Add a colorbar to the Axes
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array(plot_data["Average Temperature (°C)"])  # Associate the mappable with data
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical')
        cbar.set_label("Outdoor Temperature (°C)")
        
        # Add a title/subtitle
        plt.title(
            "9 months of Electrify America Charging Sessions\n(2024 Ioniq 6 SEL)",
            fontsize=20,          # Increase font size for emphasis
            fontweight='bold',    # Make the font bold
            color='black',        # Set the font color (adjust based on your background)
            bbox=dict(            # Add a bounding box
                facecolor='white', # Background color of the box
                edgecolor='black', # Border color of the box
                boxstyle='round,pad=0.5'  # Rounded corners and padding
            )
)

        notes = (
            "Notes: All Charges on 350 kw DC chargers. "
            "Effective speed is calculated as kWh delivered / time. "
            "Starting percentage assumes 92% efficiency."
        )
        plt.suptitle(
            notes,
            fontsize=10,
            color='black',
            style='italic',
            x=0.41, 
            y=0.02,
            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round')
        )

        ax.set_xlim(0, 100)
        ax.grid(False)

        ax.invert_yaxis()
        ax.set_xticklabels([])
        ax.set_yticklabels([]) # Removes the labels
        plt.tight_layout()

        # Save and optionally display the plot
        save_and_show_plot(plt, "electrify_america.png", dpi=300)

    def plot_temperature_vs_charge_rate(self):
        data = pd.read_csv(self.output_file)

        # Convert relevant columns
        data["Effective Charging Speed"] = pd.to_numeric(data["Effective Charging Speed"], errors='coerce')
        data["Minutes Charging"] = pd.to_numeric(data["Minutes Charging"], errors='coerce')
        data["Average Temperature (°C)"] = pd.to_numeric(data["Average Temperature (°C)"], errors='coerce')

        # Drop rows with missing essential data
        scatter_data = data.dropna(subset=["Effective Charging Speed", "Minutes Charging"])
        
        # Create the scatter plot
        plt.style.use("cyberpunk")
        plt.figure(figsize=(10, 6))
        cmap = plt.cm.coolwarm

        # Normalize minutes charging for color mapping
        norm = Normalize(
            vmin=scatter_data["Minutes Charging"].min(),
            vmax=scatter_data["Minutes Charging"].max()
        )

        # Scatter plot
        scatter = plt.scatter(
            scatter_data["Average Temperature (°C)"],
            scatter_data["Effective Charging Speed"],
            c=scatter_data["Minutes Charging"],
            cmap=cmap,
            norm=norm,
            edgecolor='k',
            # s=scatter_data["Total Energy Delivered"]  # Adjust size of markers
        )

        # Add colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label("Minutes Spent Charging", fontsize=12)

        # Add labels and title
        plt.title("Temperature vs Effective Charge Rate", fontsize=16)
        plt.xlabel("Average Temperature (°C)", fontsize=14)
        plt.ylabel("Effective Charging Speed (kW)", fontsize=14)
        plt.tight_layout()

        # Save and optionally display the plot
        save_and_show_plot(plt, "temperature_vs_charge_rate.png", dpi=300)

    def process_emails(self):
        """
        Process all .eml files, extract metadata, and write to a CSV file.
        If the output CSV already exists, load and return its contents instead of processing emails again.
        """
        # Check if cached CSV file exists
        if os.path.exists(self.output_file):
            print(f"Loading cached data from {self.output_file}")
            with open(self.output_file, 'r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                cached_data = list(reader)
            return cached_data

        # Process .eml files if no cached CSV exists
        email_files = [f for f in os.listdir(self.input_dir) if f.endswith('.eml')]
        extracted_data = []

        for email_file in email_files:
            email_path = os.path.join(self.input_dir, email_file)
            with open(email_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)

            email_content = ""
            if msg.is_multipart():
                for part in msg.iter_parts():
                    if part.get_content_type() == "text/plain":
                        email_content = part.get_content()
                        break
            else:
                email_content = msg.get_content()

            metadata = self.extract_charge_metadata(email_content, email_file)
            metadata = self.calculate_columns(metadata)
            metadata = self.calculate_temp(metadata)
            extracted_data.append(metadata)

        # Write extracted data to a CSV file
        if extracted_data:
            fieldnames = extracted_data[0].keys()
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(extracted_data)

        return extracted_data

