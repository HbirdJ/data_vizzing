from data_vizzing.electrify_america import EmailProcessor

# Set input and output paths
input_dir = "./data/electrify_america/easessionsummaries"
output_file = "./data/electrify_america/charging_sessions.csv"

processor = EmailProcessor(input_dir, output_file)
processor.process_emails()
print(f"Extraction completed. Data saved to {output_file}")
processor.plot_charge_events()
processor.plot_temperature_vs_charge_rate()