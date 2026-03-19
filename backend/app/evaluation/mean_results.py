import pandas as pd

df = pd.read_csv("scored_results_structured.csv")

print("Airbot Mean Scores:")
print(df[[col for col in df.columns if "Airbot" in col]].mean())

print("NVIDIA Mean Scores:")
print(df[[col for col in df.columns if "NVIDIA" in col]].mean())